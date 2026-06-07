import { Hanken_Grotesk, Source_Serif_4 } from 'next/font/google';
import './globals.css';

const hanken = Hanken_Grotesk({
  subsets: ['latin'],
  variable: '--font-body',
  display: 'swap',
});

const sourceSerif = Source_Serif_4({
  subsets: ['latin'],
  variable: '--font-heading',
  display: 'swap',
});

export const metadata = {
  title: 'CuePoint AI',
  description: 'Ask questions about YouTube podcasts and jump to timestamps',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${hanken.variable} ${sourceSerif.variable}`}>
      <body>{children}</body>
    </html>
  );
}
