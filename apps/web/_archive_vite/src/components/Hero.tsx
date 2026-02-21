import { useEffect, useState } from "react";
import { Star } from "lucide-react";
import WaitlistForm from "./WaitlistForm";
import { fetchWaitlistCount } from "../lib/api";

export default function Hero() {
  const [waitlistCount, setWaitlistCount] = useState(247);

  useEffect(() => {
    fetchWaitlistCount().then(setWaitlistCount);
  }, []);

  return (
    <section className="pt-32 pb-20 bg-white">
      <div className="max-w-6xl mx-auto px-6">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h1 className="text-5xl md:text-6xl font-bold leading-tight mb-6">
              Inteligência essencial,
              <br />
              não superficial.
            </h1>

            <p className="text-lg text-gray-700 mb-8 leading-relaxed">
              Toda segunda-feira, os dados mais relevantes sobre o ecossistema tech da América
              Latina — pesquisados por agentes de IA auditáveis, revisados por humanos, entregues no
              seu inbox.
            </p>

            <div className="mb-8">
              <WaitlistForm />
            </div>

            <div className="border-t border-gray-200 pt-6">
              <div className="flex items-center space-x-2 mb-3">
                <div className="flex">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="w-4 h-4 fill-red-600 text-red-600" />
                  ))}
                </div>
                <span className="text-sm font-medium">
                  +{waitlistCount.toLocaleString("pt-BR")} fundadores, CTOs e investidores já leem o
                  Sinal
                </span>
              </div>

              <p className="text-sm text-gray-600 italic">
                "A única newsletter que leio inteira" — CTO, Startup LATAM
              </p>
            </div>
          </div>

          <div className="relative">
            <div className="bg-gray-50 border-2 border-gray-200 rounded-lg p-8 shadow-xl">
              <div className="mb-4">
                <div className="text-xs text-gray-500 mb-2">BRIEFING SINAL · Edição #47</div>
                <div className="text-2xl font-bold mb-4">📡 Radar da Semana</div>
              </div>

              <div className="space-y-4">
                <div className="bg-white p-4 rounded border border-gray-200">
                  <div className="text-sm font-medium mb-2">Funding LATAM</div>
                  <div className="text-3xl font-bold text-red-600">US$287M</div>
                  <div className="text-xs text-gray-500 mt-1">
                    14 deals · −12% vs. semana anterior
                  </div>
                </div>

                <div className="bg-white p-4 rounded border border-gray-200">
                  <div className="text-sm text-gray-700">
                    3 deals acima de US$50M que passaram despercebidos
                  </div>
                </div>

                <div className="bg-white p-4 rounded border border-gray-200">
                  <div className="text-xs text-gray-500 mb-1">
                    DQ: 4/5 · AC: 4/5 · Revisado por editor
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full w-4/5 bg-red-600"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
