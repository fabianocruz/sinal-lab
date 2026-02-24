interface LegalSectionProps {
  id: string;
  num: string;
  title: string;
  children: React.ReactNode;
}

export default function LegalSection({ id, num, title, children }: LegalSectionProps) {
  return (
    <section id={id} className="mb-10 scroll-mt-[100px]">
      <h2 className="mb-4 flex items-baseline gap-2.5 border-b border-sinal-slate pb-3 font-display text-xl font-normal text-sinal-white">
        <span className="font-mono text-[13px] text-[#4A4A56]">{num}.</span>
        {title}
      </h2>
      <div className="text-sm leading-[1.85] text-silver">{children}</div>
    </section>
  );
}
