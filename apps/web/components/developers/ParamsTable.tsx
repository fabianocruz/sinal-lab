import type { ApiParam } from "@/lib/api-docs";

interface ParamsTableProps {
  params: ApiParam[];
}

export default function ParamsTable({ params }: ParamsTableProps) {
  if (params.length === 0) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-[rgba(255,255,255,0.1)]">
            <th className="px-3 py-2 font-mono text-[11px] uppercase tracking-[1px] text-ash">
              Parâmetro
            </th>
            <th className="px-3 py-2 font-mono text-[11px] uppercase tracking-[1px] text-ash">
              Tipo
            </th>
            <th className="px-3 py-2 font-mono text-[11px] uppercase tracking-[1px] text-ash">
              Default
            </th>
            <th className="px-3 py-2 font-mono text-[11px] uppercase tracking-[1px] text-ash">
              Descrição
            </th>
          </tr>
        </thead>
        <tbody>
          {params.map((param) => (
            <tr key={param.name} className="border-b border-[rgba(255,255,255,0.04)]">
              <td className="px-3 py-2.5">
                <code className="font-mono text-[13px] text-sinal-white">{param.name}</code>
                {param.required && (
                  <span className="ml-2 rounded bg-[rgba(255,138,89,0.12)] px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-[0.5px] text-[#FF8A59]">
                    obrigatório
                  </span>
                )}
              </td>
              <td className="px-3 py-2.5 font-mono text-[12px] text-signal">{param.type}</td>
              <td className="px-3 py-2.5 font-mono text-[12px] text-ash">
                {param.default ?? "\u2014"}
              </td>
              <td className="px-3 py-2.5 text-[13px] text-silver">{param.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
