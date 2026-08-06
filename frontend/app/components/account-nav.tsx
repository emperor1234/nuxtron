const ACCOUNT_LINKS = [
  { href: '/account', label: 'Overview' },
  { href: '/account/profile', label: 'Personal Details' },
  { href: '/account/orders', label: 'Orders' },
  { href: '/account/wallet', label: 'Wallet Credits' },
  { href: '/account/settings', label: 'Settings' },
];

export default function AccountNav() {
  return (
    <aside className="account-nav">
      <h3>Account</h3>
      {ACCOUNT_LINKS.map((link) => (
        <a key={link.href} href={link.href}>
          {link.label}
        </a>
      ))}
    </aside>
  );
}
