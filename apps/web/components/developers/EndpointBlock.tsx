import type { EndpointDoc } from "@/lib/api-docs";
import ParamsTable from "./ParamsTable";
import FieldsTable from "./FieldsTable";
import CodeTabs from "./CodeTabs";

interface EndpointBlockProps {
  endpoint: EndpointDoc;
}

export default function EndpointBlock({ endpoint }: EndpointBlockProps) {
  return (
    <div className="rounded-xl border border-[rgba(255,255,255,0.06)] bg-sinal-graphite">
      {/* Header — method badge + path */}
      <div className="flex items-center gap-3 border-b border-[rgba(255,255,255,0.04)] px-5 py-3">
        <span className="rounded bg-[rgba(232,255,89,0.12)] px-2 py-0.5 font-mono text-[11px] font-semibold text-signal">
          {endpoint.method}
        </span>
        <code className="font-mono text-[13px] text-sinal-white">{endpoint.path}</code>
      </div>

      <div className="space-y-6 px-5 py-5">
        {/* Description */}
        <p className="text-[14px] leading-relaxed text-silver">{endpoint.description}</p>

        {/* Parameters */}
        {endpoint.params.length > 0 && (
          <div>
            <h4 className="mb-3 font-mono text-[11px] font-semibold uppercase tracking-[1.5px] text-ash">
              Parâmetros
            </h4>
            <div className="rounded-lg border border-[rgba(255,255,255,0.04)] bg-sinal-black">
              <ParamsTable params={endpoint.params} />
            </div>
          </div>
        )}

        {/* Response fields */}
        <div>
          <h4 className="mb-3 font-mono text-[11px] font-semibold uppercase tracking-[1.5px] text-ash">
            Campos da Resposta
          </h4>
          <div className="rounded-lg border border-[rgba(255,255,255,0.04)] bg-sinal-black">
            <FieldsTable fields={endpoint.responseFields} />
          </div>
        </div>

        {/* Code examples */}
        <div>
          <h4 className="mb-3 font-mono text-[11px] font-semibold uppercase tracking-[1.5px] text-ash">
            Exemplo
          </h4>
          <CodeTabs examples={endpoint.examples} response={endpoint.exampleResponse} />
        </div>
      </div>
    </div>
  );
}
