"use client";

import { useRouter, useSearchParams } from "next/navigation";

export type SignalsTab = "pulse" | "voices" | "memo";

interface Tab {
  key: SignalsTab;
  label: string;
  icon: string;
}

const TABS: Tab[] = [
  { key: "pulse", label: "Pulse Geral", icon: "◎" },
  { key: "voices", label: "Top Voices", icon: "◈" },
  { key: "memo", label: "Memo Semanal", icon: "◉" },
];

interface TabNavProps {
  activeTab: SignalsTab;
}

export default function TabNav({ activeTab }: TabNavProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function handleTabClick(tab: SignalsTab) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", tab);
    // Clear pagination/filter params when switching tabs
    params.delete("page");
    params.delete("platform");
    params.delete("type");
    router.push(`/signals?${params.toString()}`);
  }

  return (
    <nav
      className="flex gap-1 overflow-x-auto pb-px"
      role="tablist"
      aria-label="Paineis do dashboard"
    >
      {TABS.map((tab) => {
        const isActive = activeTab === tab.key;
        return (
          <button
            key={tab.key}
            role="tab"
            aria-selected={isActive}
            aria-controls={`panel-${tab.key}`}
            onClick={() => handleTabClick(tab.key)}
            className={[
              "flex shrink-0 items-center gap-2 whitespace-nowrap rounded-t-lg border border-b-0 px-4 py-2.5 font-mono text-[12px] uppercase tracking-[1px] transition-all duration-200",
              isActive
                ? "border-sinal-slate bg-sinal-graphite text-sinal-white"
                : "border-transparent text-ash hover:text-silver",
            ].join(" ")}
          >
            <span aria-hidden="true" className="text-[10px]">
              {tab.icon}
            </span>
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
}
