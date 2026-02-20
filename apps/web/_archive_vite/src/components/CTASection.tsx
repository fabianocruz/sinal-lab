import { useEffect, useState } from "react";
import Section from "./Section";
import WaitlistForm from "./WaitlistForm";
import { fetchWaitlistCount } from "../lib/api";

export default function CTASection() {
  const [waitlistCount, setWaitlistCount] = useState(247);

  useEffect(() => {
    fetchWaitlistCount().then(setWaitlistCount);
  }, []);

  return (
    <Section dark>
      <div className="text-center max-w-3xl mx-auto">
        <h2 className="text-4xl font-bold mb-6">Pronto para receber inteligência de verdade?</h2>
        <p className="text-lg text-gray-300 mb-8">
          O próximo Briefing sai na segunda-feira. Junte-se a{" "}
          {waitlistCount.toLocaleString("pt-BR")} fundadores, CTOs e investidores que começam a
          semana com os dados certos.
        </p>

        <WaitlistForm />
      </div>
    </Section>
  );
}
