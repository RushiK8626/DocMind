import Sidebar from './Sidebar';

/**
 * Main layout wrapper: sidebar + content area.
 * Used for authenticated pages.
 */
export default function Layout({ children }) {
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">{children}</main>
    </div>
  );
}
