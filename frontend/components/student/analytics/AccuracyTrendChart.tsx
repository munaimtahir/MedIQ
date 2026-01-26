"use client";

import { memo, useMemo } from "react";
import { Card } from "@/components/ui/card";
import type { DailyTrend } from "@/lib/types/analytics";
import { format, parseISO } from "@/lib/dateUtils";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface AccuracyTrendChartProps {
  data: DailyTrend[];
  title?: string;
}

export const AccuracyTrendChart = memo(function AccuracyTrendChart({ 
  data, 
  title = "Accuracy Trend" 
}: AccuracyTrendChartProps) {
  // Memoize chart data transformation
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];
    
    return data.map((item) => ({
      date: format(parseISO(item.date), "MMM d"),
      accuracy: item.accuracy_pct,
      attempted: item.attempted,
    }));
  }, [data]);
  
  if (!data || data.length === 0) {
    return (
      <Card className="p-6">
        <h3 className="mb-4 text-lg font-semibold">{title}</h3>
        <div className="flex h-[200px] items-center justify-center text-sm text-muted-foreground">
          No trend data available
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <h3 className="mb-4 text-lg font-semibold">{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData}>
          <XAxis dataKey="date" stroke="#888888" fontSize={12} tickLine={false} axisLine={false} />
          <YAxis
            stroke="#888888"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            domain={[0, 100]}
            tickFormatter={(value) => `${value}%`}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (active && payload && payload.length) {
                return (
                  <div className="rounded-lg border bg-background p-2 shadow-sm">
                    <div className="grid grid-cols-2 gap-2">
                      <div className="flex flex-col">
                        <span className="text-[0.70rem] uppercase text-muted-foreground">Date</span>
                        <span className="font-bold text-foreground">{payload[0].payload.date}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[0.70rem] uppercase text-muted-foreground">
                          Accuracy
                        </span>
                        <span className="font-bold text-foreground">{payload[0].value}%</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[0.70rem] uppercase text-muted-foreground">
                          Questions
                        </span>
                        <span className="font-bold text-foreground">
                          {payload[0].payload.attempted}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              }
              return null;
            }}
          />
          <Line
            type="monotone"
            dataKey="accuracy"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
});
