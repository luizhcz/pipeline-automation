import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: Date, includeTime = false): string {
  if (!date) return "-"

  const options: Intl.DateTimeFormatOptions = {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }

  if (includeTime) {
    options.hour = "2-digit"
    options.minute = "2-digit"
    options.second = "2-digit"
  }

  return new Intl.DateTimeFormat("pt-BR", options).format(date instanceof Date ? date : new Date(date))
}
