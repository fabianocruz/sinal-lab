import { Menu, X } from 'lucide-react';
import { useState } from 'react';
import Button from './Button';

export default function Navbar() {
  const [isOpen, setIsOpen] = useState(false);

  const links = [
    { label: 'Briefing', href: '#briefing' },
    { label: 'Índices', href: '#indices' },
    { label: 'Comunidade', href: '#comunidade' },
    { label: 'Metodologia', href: '#metodologia' },
    { label: 'Para Empresas', href: '#empresas' },
    { label: 'Preços', href: '#precos' }
  ];

  return (
    <nav className="fixed top-0 w-full bg-white border-b border-gray-200 z-50">
      <div className="max-w-6xl mx-auto px-6">
        <div className="flex justify-between items-center h-16">
          <div className="text-2xl font-bold">SINAL</div>

          <div className="hidden md:flex items-center space-x-8">
            {links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm hover:text-red-600 transition-colors"
              >
                {link.label}
              </a>
            ))}
            <Button size="sm">Assine o Briefing →</Button>
          </div>

          <button
            className="md:hidden"
            onClick={() => setIsOpen(!isOpen)}
          >
            {isOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {isOpen && (
          <div className="md:hidden py-4 space-y-4">
            {links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="block text-sm hover:text-red-600 transition-colors"
                onClick={() => setIsOpen(false)}
              >
                {link.label}
              </a>
            ))}
            <Button size="sm" className="w-full">Assine o Briefing →</Button>
          </div>
        )}
      </div>
    </nav>
  );
}
