import { cn } from "@/lib/utils"
import type { ExecutionStatus } from "@/types/execution"

interface StatusBadgeProps {
  status: ExecutionStatus
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        status === "PENDING" && "bg-yellow-100 text-yellow-800",
        status === "STARTED" && "bg-blue-100 text-blue-800 animate-pulse",
        status === "SUCCESS" && "bg-green-100 text-green-800",
        status === "FAILURE" && "bg-red-100 text-red-800",
      )}
    >
      {status === "PENDING" && "Pendente"}
      {status === "STARTED" && "Em execução"}
      {status === "SUCCESS" && "Sucesso"}
      {status === "FAILURE" && "Falha"}
    </span>
  )
}
