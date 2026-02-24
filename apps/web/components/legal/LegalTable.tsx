interface LegalTableProps {
  headers: string[];
  rows: string[][];
}

export default function LegalTable({ headers, rows }: LegalTableProps) {
  return (
    <div className="mb-4 overflow-x-auto rounded-lg border border-sinal-slate">
      <table className="w-full border-collapse font-mono text-[11px]">
        <thead>
          <tr>
            {headers.map((h) => (
              <th
                key={h}
                className="border-b border-sinal-slate bg-sinal-graphite px-3 py-2.5 text-left text-[9px] uppercase tracking-[1px] text-[#4A4A56]"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td
                  key={j}
                  className="border-b border-[rgba(255,255,255,0.06)] px-3 py-2.5 font-body text-xs text-silver"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
