import { ThemeToggle } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";
import ksqLogo from "@assets/image_1773224776245.png";
import type { LucideIcon } from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  testId: string;
}

interface PageHeaderProps {
  title: string;
  subtitle: string;
  navItems?: NavItem[];
  leftContent?: React.ReactNode;
  testId?: string;
}

export function PageHeader({ title, subtitle, navItems = [], leftContent, testId }: PageHeaderProps) {
  return (
    <header className="relative z-10 shrink-0 border-b border-gray-200/50 dark:border-[#1e1e30] px-6 py-3 flex items-center justify-between bg-white/80 dark:bg-[#0e0e1a]/90 backdrop-blur-2xl">
      <div className="flex items-center gap-3">
        {leftContent}
        <div className="w-10 h-10 rounded-xl bg-white dark:bg-[#1a1a2e] flex items-center justify-center border border-gray-200/50 dark:border-[#2a2a3d]">
          <img src={ksqLogo} alt="KSquare" className="w-6 h-6 object-contain dark:brightness-0 dark:invert" />
        </div>
        <div>
          <h1 className="font-bold text-base tracking-tight text-gray-900 dark:text-white" data-testid={testId}>{title}</h1>
          <p className="text-[11px] text-gray-500 dark:text-slate-500">{subtitle}</p>
        </div>
      </div>
      <div className="flex items-center gap-1.5">
        <ThemeToggle />
        {navItems.map((item) => (
          <Link key={item.href} href={item.href}>
            <Button data-testid={item.testId} variant="ghost" size="sm" className="gap-1.5 text-gray-700 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-white/[0.06] text-xs h-8">
              <item.icon className="w-3.5 h-3.5" />
              {item.label}
            </Button>
          </Link>
        ))}
      </div>
    </header>
  );
}
