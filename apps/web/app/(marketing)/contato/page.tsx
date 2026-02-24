import type { Metadata } from "next";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import Section from "@/components/layout/Section";
import ContatoForm from "@/components/contato/ContatoForm";

export const metadata: Metadata = {
  title: "Contato",
  description:
    "Entre em contato com a equipe da Sinal — dúvidas, parcerias, imprensa ou requisições LGPD.",
  openGraph: {
    title: "Contato | Sinal",
    description:
      "Entre em contato com a equipe da Sinal — dúvidas, parcerias, imprensa ou requisições LGPD.",
    type: "website",
  },
};

export default function ContatoPage() {
  return (
    <>
      <Navbar />
      <main className="pt-[72px]">
        <Section label="CONTATO">
          <h1 className="font-display text-[clamp(32px,5vw,42px)] leading-tight text-sinal-white">
            Fale com a Sinal.
          </h1>
          <p className="mt-3.5 max-w-[480px] text-[16px] leading-relaxed text-silver">
            Selecione o assunto e envie sua mensagem. Respondemos em até{" "}
            <span className="font-medium text-signal">48 horas úteis</span>.
          </p>
        </Section>

        <section className="border-b border-[rgba(255,255,255,0.04)] py-8 pb-20">
          <div className="mx-auto max-w-[720px] px-6 md:px-10">
            <ContatoForm />
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
