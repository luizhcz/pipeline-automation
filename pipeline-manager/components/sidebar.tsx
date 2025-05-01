"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { PlusCircle, List, Play, Activity } from "lucide-react"

export default function Sidebar() {
  const pathname = usePathname()

  const links = [
    {
      href: "/new-pipeline",
      label: "Novo Pipeline",
      icon: PlusCircle,
    },
    {
      href: "/my-pipelines",
      label: "Meus Pipelines",
      icon: List,
    },
    {
      href: "/execute-pipeline",
      label: "Executar Pipeline",
      icon: Play,
    },
    {
      href: "/monitor-executions",
      label: "Monitorar Execuções",
      icon: Activity,
    },
  ]

  return (
    <aside className="w-64 bg-card border-r h-screen">
      <div className="p-4 border-b">
        <h1 className="text-xl font-bold">Pipeline Manager</h1>
      </div>
      <nav className="p-2">
        <ul className="space-y-1">
          {links.map((link) => {
            const Icon = link.icon
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    pathname === link.href
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-accent hover:text-accent-foreground",
                  )}
                >
                  <Icon className="h-5 w-5" />
                  {link.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
    </aside>
  )
}
