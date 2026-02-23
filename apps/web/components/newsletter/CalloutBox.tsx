import { Callout } from "@/lib/newsletter";

interface CalloutBoxProps {
  /** Callout data (type, content, position) from newsletter metadata_. */
  callout: Callout;
  /** Agent accent color used as border for "highlight" type callouts. */
  agentColor: string;
}

/**
 * Styled aside for editorial callouts (highlights, notes, warnings).
 * Border color: highlight = agentColor, note = blue (#59B4FF), warning = amber (#FFB459).
 */
const TYPE_STYLES: Record<Callout["type"], { borderColor: string; label: string }> = {
  highlight: { borderColor: "", label: "DESTAQUE" },
  note: { borderColor: "#59B4FF", label: "NOTA" },
  warning: { borderColor: "#FFB459", label: "ATENCAO" },
};

export default function CalloutBox({ callout, agentColor }: CalloutBoxProps) {
  const knownType = callout.type in TYPE_STYLES;
  const style = knownType ? TYPE_STYLES[callout.type] : TYPE_STYLES.highlight;
  const borderColor = callout.type === "highlight" || !knownType ? agentColor : style.borderColor;

  return (
    <aside
      className="my-8 rounded-r-lg border-l-2 bg-sinal-graphite px-5 py-4"
      style={{ borderColor }}
    >
      <span
        className="mb-2 block font-mono text-[10px] uppercase tracking-[2px]"
        style={{ color: borderColor }}
      >
        {style.label}
      </span>
      <p className="text-[15px] leading-[1.7] text-silver">{callout.content}</p>
    </aside>
  );
}
