import { useQuery } from "@tanstack/react-query";
import { useParams } from "wouter";
import { ThemeToggle } from "@/components/theme-provider";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  ListChecks,
  FileStack,
  FileText,
  Users,
  AlertTriangle,
  MapPin,
} from "lucide-react";
import { Link } from "wouter";
import type { LoanPhase } from "@shared/schema";
import ksqLogo from "@assets/image_1773224776245.png";
import { getPhaseIcon, getPhaseContent } from "@/constants/phase-knowledge";

function SectionHeader({ icon: Icon, title, color }: { icon: typeof Clock; title: string; color: string }) {
  return (
    <div className="flex items-center gap-2.5 mb-4">
      <div
        className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
        style={{ backgroundColor: `${color}18`, color }}
      >
        <Icon className="w-4 h-4" />
      </div>
      <h3 className="text-sm font-semibold text-slate-800 dark:text-white">{title}</h3>
    </div>
  );
}

export default function PhaseDetail() {
  const params = useParams<{ id: string }>();
  const phaseId = params.id;

  const { data: phases, isLoading } = useQuery<LoanPhase[]>({
    queryKey: ["/api/phases"],
  });

  const phase = phases?.find((p) => p.id === phaseId);
  const content = phase ? getPhaseContent(phase.name) : null;
  const PhaseIcon = phase ? getPhaseIcon(phase.icon) : CheckCircle2;
  const phaseColor = phase?.color || "#3b82f6";

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-[#0e1015] p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          <Skeleton className="h-10 w-48" />
          <Skeleton className="h-40 w-full rounded-2xl" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Skeleton className="h-60 w-full rounded-2xl" />
            <Skeleton className="h-60 w-full rounded-2xl" />
          </div>
        </div>
      </div>
    );
  }

  if (!phase) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-[#0e1015] flex items-center justify-center p-6">
        <Card className="p-8 text-center max-w-md">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-slate-800 dark:text-white mb-2" data-testid="text-phase-not-found">Phase Not Found</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mb-6">The requested loan phase could not be found.</p>
          <Link href="/">
            <Button data-testid="button-back-home" className="gap-2">
              <ArrowLeft className="w-4 h-4" />
              Back to Home
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  const sortedPhases = phases?.filter((p) => p.isActive).sort((a, b) => a.sortOrder - b.sortOrder) || [];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0e1015]">
      <header className="sticky top-0 z-50 bg-white/80 dark:bg-[#0e1015]/80 backdrop-blur-xl border-b border-slate-200/60 dark:border-white/[0.06]">
        <div className="max-w-4xl mx-auto px-6 py-3 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3 flex-wrap">
            <button onClick={() => window.history.back()} data-testid="button-back" className="flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-white transition-colors">
              <ArrowLeft className="w-4 h-4" />
              Back
            </button>
            <div className="w-px h-5 bg-slate-200 dark:bg-white/[0.08]" />
            <img src={ksqLogo} alt="KSquare" className="h-7 object-contain dark:brightness-0 dark:invert" data-testid="img-ksquare-logo" />
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        <div className="flex items-start gap-4 flex-wrap">
          <div
            className="w-14 h-14 rounded-xl flex items-center justify-center shrink-0"
            style={{ backgroundColor: `${phaseColor}18`, color: phaseColor }}
            data-testid="icon-phase"
          >
            <PhaseIcon className="w-7 h-7" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3 mb-1 flex-wrap">
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white" data-testid="text-phase-name">{phase.name}</h1>
              <Badge
                className="text-[10px] font-bold border-transparent"
                style={{ backgroundColor: `${phaseColor}18`, color: phaseColor }}
              >
                Phase {phase.sortOrder}
              </Badge>
            </div>
            {phase.description && (
              <p className="text-sm text-slate-500 dark:text-slate-400" data-testid="text-phase-description">{phase.description}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-2 flex-wrap">
          {sortedPhases.map((p) => (
            <Link key={p.id} href={`/phases/${p.id}`}>
              <Badge
                data-testid={`badge-phase-nav-${p.id}`}
                className={`text-[10px] font-medium cursor-pointer whitespace-nowrap border-transparent ${
                  p.id === phaseId
                    ? "text-white"
                    : "bg-slate-100 dark:bg-white/[0.06] text-slate-500 dark:text-slate-400"
                }`}
                style={p.id === phaseId ? { backgroundColor: phaseColor, color: "white" } : {}}
              >
                {p.sortOrder}. {p.name}
              </Badge>
            </Link>
          ))}
        </div>

        <Card className="p-6" data-testid="card-summary">
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
              style={{ backgroundColor: `${phaseColor}18`, color: phaseColor }}
            >
              <MapPin className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-semibold text-slate-800 dark:text-white">Overview</h3>
            <Badge className="text-[10px] font-medium bg-blue-500/10 text-blue-600 dark:text-blue-300 border-transparent gap-1">
              <Clock className="w-3 h-3" />
              {content?.timeline}
            </Badge>
          </div>
          <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed" data-testid="text-phase-summary">
            {content?.summary}
          </p>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="p-6" data-testid="card-activities">
            <SectionHeader icon={ListChecks} title="Key Activities" color="#3b82f6" />
            <ul className="space-y-2.5">
              {content?.activities.map((activity, i) => (
                <li key={i} className="flex items-start gap-2.5" data-testid={`text-activity-${i}`}>
                  <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0 text-emerald-500 dark:text-emerald-400" />
                  <span className="text-sm text-slate-600 dark:text-slate-300">{activity}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-6" data-testid="card-documents">
            <SectionHeader icon={FileStack} title="Required Documents" color="#8b5cf6" />
            <ul className="space-y-2.5">
              {content?.documents.map((doc, i) => (
                <li key={i} className="flex items-start gap-2.5" data-testid={`text-document-${i}`}>
                  <FileText className="w-4 h-4 mt-0.5 shrink-0 text-violet-500 dark:text-violet-400" />
                  <span className="text-sm text-slate-600 dark:text-slate-300">{doc}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-6" data-testid="card-stakeholders">
            <SectionHeader icon={Users} title="Stakeholders Involved" color="#0ea5e9" />
            <ul className="space-y-2.5">
              {content?.stakeholders.map((person, i) => (
                <li key={i} className="flex items-start gap-2.5" data-testid={`text-stakeholder-${i}`}>
                  <Users className="w-4 h-4 mt-0.5 shrink-0 text-sky-500 dark:text-sky-400" />
                  <span className="text-sm text-slate-600 dark:text-slate-300">{person}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="p-6" data-testid="card-bottlenecks">
            <SectionHeader icon={AlertTriangle} title="Common Bottlenecks" color="#f59e0b" />
            <ul className="space-y-2.5">
              {content?.bottlenecks.map((issue, i) => (
                <li key={i} className="flex items-start gap-2.5" data-testid={`text-bottleneck-${i}`}>
                  <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-500 dark:text-amber-400" />
                  <span className="text-sm text-slate-600 dark:text-slate-300">{issue}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </main>
    </div>
  );
}
