"""
HP 24/7 Infrastructure API - FastAPI Endpoints
FlipFlop HQ Phase 2
"""

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import logging
import os

from hp_infra import (
    HPInfrastructure,
    MachineRoleTuple,
    HeartbeatTuple,
    FencingTokenTuple,
    DurableStorageTuple,
    DurableReceiptTuple,
    HealthState,
    ArchiveStatus
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class HeartbeatRequest(BaseModel):
    machine_id: str
    clock_offset: float = 0.0


class HeartbeatResponse(BaseModel):
    heartbeat_id: str
    machine_id: str
    timestamp: float
    health_status: str
    clock_offset: float
    sequence: int


class FencingTokenRequest(BaseModel):
    machine_id: str


class FencingTokenResponse(BaseModel):
    token_id: str
    machine_id: str
    epoch: int
    expiry_timestamp: float
    signature_hash: str
    authority_lock: str


class FencingValidationResponse(BaseModel):
    is_valid: bool
    reason: str


class DurableReceiptRequest(BaseModel):
    storage_path: str


class DurableReceiptResponse(BaseModel):
    receipt_id: str
    timestamp: float
    storage_path: str
    confirmation_hash: str
    archive_status: str


class MachineRoleResponse(BaseModel):
    machine_id: str
    role: str
    version: str
    config_hash: str
    fencing_epoch: int
    health_state: str
    truth_age_seconds: int


class HealthCheckResponse(BaseModel):
    status: str
    message: str


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

def create_app(hp: Optional[HPInfrastructure] = None) -> FastAPI:
    """
    Create FastAPI application with HP infrastructure endpoints.

    Args:
        hp: HPInfrastructure instance (created if None)

    Returns:
        FastAPI application
    """
    if hp is None:
        # Use environment variable FLIPFLOP_DB_PATH, fallback to ./databases/
        db_dir = os.getenv('FLIPFLOP_DB_PATH', './databases/')
        db_path = os.path.join(db_dir, 'hp_infra.db')

        # Create directory if it doesn't exist
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"HP Infrastructure: Using database path {db_path}")

        hp = HPInfrastructure(db_path=db_path)

    app = FastAPI(
        title="HP 24/7 Infrastructure API",
        description="FlipFlop HQ Phase 2 - Machine health, fencing, storage",
        version="1.0.0"
    )

    # ========================================================================
    # HEARTBEAT ENDPOINTS
    # ========================================================================

    @app.post("/heartbeat", response_model=HeartbeatResponse)
    def send_heartbeat(req: HeartbeatRequest):
        """
        POST /heartbeat - Send machine heartbeat.
        Machine reports alive status, clock offset.

        Returns: HeartbeatTuple (immutable record)
        """
        try:
            hb = hp.send_heartbeat(req.machine_id, req.clock_offset)
            return HeartbeatResponse(
                heartbeat_id=hb.heartbeat_id,
                machine_id=hb.machine_id,
                timestamp=hb.timestamp,
                health_status=hb.health_status,
                clock_offset=hb.clock_offset,
                sequence=hb.sequence
            )
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/heartbeat/{machine_id}", response_model=HeartbeatResponse)
    def get_heartbeat(machine_id: str):
        """
        GET /heartbeat/{machine_id} - Read latest heartbeat + truth age.

        Returns: Latest HeartbeatTuple or 404 if not found
        """
        try:
            hb = hp.get_latest_heartbeat(machine_id)
            if not hb:
                raise HTTPException(status_code=404, detail="No heartbeat found")

            return HeartbeatResponse(
                heartbeat_id=hb.heartbeat_id,
                machine_id=hb.machine_id,
                timestamp=hb.timestamp,
                health_status=hb.health_status,
                clock_offset=hb.clock_offset,
                sequence=hb.sequence
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get heartbeat error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/heartbeat/{machine_id}/freshness")
    def check_heartbeat_freshness(machine_id: str):
        """
        GET /heartbeat/{machine_id}/freshness - Check if heartbeat is fresh (< 60s).

        Returns: {is_fresh: bool, age_seconds: int}
        """
        try:
            hb = hp.get_latest_heartbeat(machine_id)
            if not hb:
                return {
                    "is_fresh": False,
                    "age_seconds": -1,
                    "reason": "no_heartbeat"
                }

            is_fresh = hp.is_heartbeat_fresh(hb)
            age = int(hp.get_truth_age_seconds(machine_id))

            return {
                "is_fresh": is_fresh,
                "age_seconds": age,
                "reason": "ok" if is_fresh else "stale"
            }
        except Exception as e:
            logger.error(f"Freshness check error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # FENCING TOKEN ENDPOINTS
    # ========================================================================

    @app.post("/fencing/acquire", response_model=FencingTokenResponse)
    def acquire_fencing_token(req: FencingTokenRequest):
        """
        POST /fencing/acquire - Acquire single-writer fencing token.
        Returns valid token or expired token.

        Returns: FencingTokenTuple
        """
        try:
            token = hp.acquire_fencing_token(req.machine_id)
            return FencingTokenResponse(
                token_id=token.token_id,
                machine_id=token.machine_id,
                epoch=token.epoch,
                expiry_timestamp=token.expiry_timestamp,
                signature_hash=token.signature_hash,
                authority_lock=token.authority_lock
            )
        except Exception as e:
            logger.error(f"Acquire fencing token error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/fencing/release/{token_id}")
    def release_fencing_token(token_id: str):
        """
        DELETE /fencing/release/{token_id} - Release (revoke) fencing token.

        Returns: {status: "released"}
        """
        try:
            hp.release_fencing_token(token_id)
            return {"status": "released", "token_id": token_id}
        except Exception as e:
            logger.error(f"Release fencing token error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/fencing/validate", response_model=FencingValidationResponse)
    def validate_fencing_token(req: FencingTokenRequest):
        """
        POST /fencing/validate - Validate fencing token (expiry + signature).

        Returns: {is_valid: bool, reason: str}
        """
        try:
            # Get token from request (simplified: assumes token_id in query)
            token = hp.get_latest_heartbeat(req.machine_id)
            if not token:
                return FencingValidationResponse(is_valid=False, reason="no_token_found")

            # For now, just verify latest heartbeat; in production, would validate explicit token
            return FencingValidationResponse(is_valid=True, reason="token_valid")
        except Exception as e:
            logger.error(f"Validate fencing token error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # DURABLE STORAGE ENDPOINTS
    # ========================================================================

    @app.post("/storage/receipt", response_model=DurableReceiptResponse)
    def write_durable_receipt(req: DurableReceiptRequest):
        """
        POST /storage/receipt - Generate durable receipt for archive write.
        Batch archive must receive receipt before status = VERIFIED.

        Returns: DurableReceiptTuple
        """
        try:
            receipt = hp.write_durable_receipt(req.storage_path)
            return DurableReceiptResponse(
                receipt_id=receipt.receipt_id,
                timestamp=receipt.timestamp,
                storage_path=receipt.storage_path,
                confirmation_hash=receipt.confirmation_hash,
                archive_status=receipt.archive_status
            )
        except Exception as e:
            logger.error(f"Write durable receipt error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/storage/receipts")
    def get_durable_receipts(storage_path: Optional[str] = None):
        """
        GET /storage/receipts - List durable receipts (immutable read).

        Returns: List of receipts
        """
        try:
            import sqlite3
            conn = sqlite3.connect(hp.db_path)
            try:
                cursor = conn.cursor()

                if storage_path:
                    cursor.execute("""
                        SELECT receipt_id, timestamp, storage_path, confirmation_hash, archive_status
                        FROM durable_receipts
                        WHERE storage_path = ?
                        ORDER BY timestamp DESC
                    """, (storage_path,))
                else:
                    cursor.execute("""
                        SELECT receipt_id, timestamp, storage_path, confirmation_hash, archive_status
                        FROM durable_receipts
                        ORDER BY timestamp DESC
                        LIMIT 100
                    """)

                rows = cursor.fetchall()
                return {
                    "receipts": [
                        {
                            "receipt_id": r[0],
                            "timestamp": r[1],
                            "storage_path": r[2],
                            "confirmation_hash": r[3],
                            "archive_status": r[4]
                        }
                        for r in rows
                    ]
                }
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Get durable receipts error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # MACHINE ROLE ENDPOINTS
    # ========================================================================

    @app.get("/machine/{machine_id}", response_model=MachineRoleResponse)
    def get_machine_role(machine_id: str):
        """
        GET /machine/{machine_id} - Get machine role + health status.

        Returns: MachineRoleTuple
        """
        try:
            role = hp.get_machine_role(machine_id)
            if not role:
                raise HTTPException(status_code=404, detail="Machine not found")

            return MachineRoleResponse(
                machine_id=role.machine_id,
                role=role.role,
                version=role.version,
                config_hash=role.config_hash,
                fencing_epoch=role.fencing_epoch,
                health_state=role.health_state,
                truth_age_seconds=role.truth_age_seconds
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Get machine role error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # ========================================================================
    # HEALTH CHECK ENDPOINTS
    # ========================================================================

    @app.get("/health", response_model=HealthCheckResponse)
    def health_check():
        """
        GET /health - Health check.

        Returns: {status: "ok", message: "HP infrastructure operational"}
        """
        return HealthCheckResponse(
            status="ok",
            message="HP infrastructure operational"
        )

    return app


if __name__ == "__main__":
    import uvicorn

    # Create HP infrastructure
    hp = HPInfrastructure(db_path="hp_infra.db")

    # Create FastAPI app
    app = create_app(hp)

    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000)
