/**
 * Small status indicator: "● Online" or "● Offline"
 */
export default function StatusIndicator({ isOnline = true, label = 'Online' }) {
  return (
    <div
      className={`status-indicator ${isOnline ? 'online' : 'offline'}`}
      role="status"
      aria-label={`Status: ${label}`}
    >
      <span className="status-indicator-dot" aria-hidden="true" />
      <span className="status-indicator-label">{label}</span>
    </div>
  );
}
