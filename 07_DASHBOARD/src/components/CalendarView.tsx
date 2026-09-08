import React, { useState } from 'react';

const CalendarView: React.FC = () => {
  const [currentMonth, setCurrentMonth] = useState(new Date('2026-09-01'));

  const daysInMonth = (date: Date) => new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  const firstDayOfMonth = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1).getDay();

  const days = Array.from({ length: daysInMonth(currentMonth) }, (_, i) => i + 1);
  const emptyDays = Array.from({ length: firstDayOfMonth }, () => null);

  // Mock trade days
  const tradeDays: Record<number, { trades: number; pnl: number }> = {
    1: { trades: 3, pnl: 125.50 },
    2: { trades: 2, pnl: -45.25 },
    3: { trades: 4, pnl: 285.75 },
    5: { trades: 5, pnl: 420.00 },
    8: { trades: 1, pnl: 52.50 },
  };

  const monthName = currentMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  const prevMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
  };

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));
  };

  return (
    <div style={{ padding: 'var(--spacing-6)' }}>
      <div
        style={{
          padding: 'var(--spacing-6)',
          background: 'var(--hq-panel-bg)',
          borderRadius: '12px',
          border: '1px solid var(--color-border)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-6)' }}>
          <h2 style={{ fontSize: 'var(--font-size-xl)', fontWeight: 'bold' }}>{monthName}</h2>
          <div style={{ display: 'flex', gap: 'var(--spacing-2)' }}>
            <button
              onClick={prevMonth}
              style={{
                padding: '8px 12px',
                background: 'rgba(51, 65, 85, 0.5)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                color: 'var(--color-text-primary)',
                cursor: 'pointer',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              ← Prev
            </button>
            <button
              onClick={nextMonth}
              style={{
                padding: '8px 12px',
                background: 'rgba(51, 65, 85, 0.5)',
                border: '1px solid var(--color-border)',
                borderRadius: '6px',
                color: 'var(--color-text-primary)',
                cursor: 'pointer',
                fontSize: 'var(--font-size-sm)',
              }}
            >
              Next →
            </button>
          </div>
        </div>

        {/* Day headers */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(7, 1fr)',
            gap: '1px',
            marginBottom: 'var(--spacing-4)',
            background: 'var(--color-border)',
            padding: '1px',
            borderRadius: '8px',
            overflow: 'hidden',
          }}
        >
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
            <div
              key={day}
              style={{
                padding: '12px',
                background: 'rgba(51, 65, 85, 0.3)',
                textAlign: 'center',
                fontWeight: '600',
                fontSize: 'var(--font-size-sm)',
                color: 'var(--color-text-secondary)',
              }}
            >
              {day}
            </div>
          ))}
        </div>

        {/* Calendar grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(7, 1fr)',
            gap: '1px',
            background: 'var(--color-border)',
            padding: '1px',
            borderRadius: '8px',
            overflow: 'hidden',
            minHeight: '300px',
          }}
        >
          {[...emptyDays, ...days].map((day, idx) => {
            const dayData = day ? tradeDays[day] : null;

            return (
              <div
                key={idx}
                style={{
                  padding: 'var(--spacing-3)',
                  background: dayData ? 'rgba(51, 65, 85, 0.5)' : 'rgba(51, 65, 85, 0.2)',
                  minHeight: '80px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'flex-start',
                  cursor: dayData ? 'pointer' : 'default',
                  transition: 'background 0.2s',
                }}
              >
                {day && (
                  <>
                    <div
                      style={{
                        fontSize: 'var(--font-size-sm)',
                        fontWeight: '600',
                        color: 'var(--color-text-primary)',
                        marginBottom: '4px',
                      }}
                    >
                      {day}
                    </div>
                    {dayData && (
                      <>
                        <div
                          style={{
                            fontSize: 'var(--font-size-xs)',
                            color: 'var(--color-text-secondary)',
                            marginBottom: '4px',
                          }}
                        >
                          {dayData.trades} trades
                        </div>
                        <div
                          style={{
                            fontSize: 'var(--font-size-sm)',
                            fontWeight: '600',
                            color: dayData.pnl > 0 ? 'var(--color-pass-green)' : 'var(--color-fail-red)',
                          }}
                        >
                          ${dayData.pnl > 0 ? '+' : ''}
                          {dayData.pnl.toFixed(2)}
                        </div>
                      </>
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default CalendarView;
