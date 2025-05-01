"use client"

import { useEffect, useState } from "react"

interface CountdownTimerProps {
  expiryDate: Date
}

export default function CountdownTimer({ expiryDate }: CountdownTimerProps) {
  const [timeLeft, setTimeLeft] = useState<string>("")
  const [isExpired, setIsExpired] = useState<boolean>(false)

  useEffect(() => {
    const calculateTimeLeft = () => {
      const now = new Date()
      const difference = expiryDate.getTime() - now.getTime()

      if (difference <= 0) {
        setIsExpired(true)
        setTimeLeft("Expirado")
        return
      }

      // Calculate hours, minutes, seconds
      const hours = Math.floor(difference / (1000 * 60 * 60))
      const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60))
      const seconds = Math.floor((difference % (1000 * 60)) / 1000)

      // Format the time left
      setTimeLeft(
        `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`,
      )
    }

    // Calculate immediately
    calculateTimeLeft()

    // Update every second
    const timer = setInterval(calculateTimeLeft, 1000)

    // Cleanup
    return () => clearInterval(timer)
  }, [expiryDate])

  return <span className={isExpired ? "text-muted-foreground" : "text-foreground"}>{timeLeft}</span>
}
