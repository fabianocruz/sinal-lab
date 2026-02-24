import type { ApiField } from "@/lib/api-docs";

interface FieldsTableProps {
  fields: ApiField[];
}

export default function FieldsTable({ fields }: FieldsTableProps) {
  if (fields.length === 0) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-[rgba(255,255,255,0.1)]">
            <th className="px-3 py-2 font-mono text-[11px] uppercase tracking-[1px] text-ash">
              Campo
            </th>
            <th className="px-3 py-2 font-mono text-[11px] uppercase tracking-[1px] text-ash">
              Tipo
            </th>
            <th className="px-3 py-2 font-mono text-[11px] uppercase tracking-[1px] text-ash">
              Descrição
            </th>
          </tr>
        </thead>
        <tbody>
          {fields.map((field) => (
            <tr key={field.name} className="border-b border-[rgba(255,255,255,0.04)]">
              <td className="px-3 py-2.5">
                <code className="font-mono text-[13px] text-sinal-white">{field.name}</code>
              </td>
              <td className="px-3 py-2.5 font-mono text-[12px] text-signal">{field.type}</td>
              <td className="px-3 py-2.5 text-[13px] text-silver">{field.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
