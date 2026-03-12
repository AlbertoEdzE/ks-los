import { CheckCircle2, XCircle } from "lucide-react";

export function PhaseActionResult({ metadata }: { metadata: any }) {
  const phaseAction = metadata?.phaseAction;
  if (!phaseAction) return null;

  return (
    <div className={`mt-2 p-3 rounded-2xl border ${
      phaseAction.success
        ? "bg-blue-50 dark:bg-blue-500/[0.06] border-blue-200/40 dark:border-blue-500/10"
        : "bg-red-50 dark:bg-red-500/10 border-red-200/40 dark:border-red-500/10"
    }`}>
      <div className="flex items-center gap-2 text-xs font-medium mb-1">
        {phaseAction.success ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
        ) : (
          <XCircle className="w-3.5 h-3.5 text-red-500 dark:text-red-400" />
        )}
        <span className={phaseAction.success ? "text-blue-700 dark:text-blue-400" : "text-red-600 dark:text-red-400"}>
          {phaseAction.success ? "Action Completed" : "Action Failed"}
        </span>
      </div>
      <p className="text-xs text-gray-500 dark:text-gray-400">{phaseAction.message}</p>
    </div>
  );
}
