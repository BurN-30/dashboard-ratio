"use client";

import { ApexOptions } from "apexcharts";
import React from "react";
import ReactApexChart from "react-apexcharts";
import { AllStats, TrackerData } from "@/types/tracker";
import { useTheme } from "@/context/ThemeContext";

interface TrackerChartProps {
  trackerName: string;
  history: AllStats[];
}

const TrackerChart: React.FC<TrackerChartProps> = ({ trackerName, history }) => {
  const [metric, setMetric] = React.useState<'ratio' | 'buffer'>('ratio');
  const { theme } = useTheme();

  const parseSize = (str: string): number => {
    if (!str) return 0;
    const cleanStr = str.replace(/,/g, '.').trim();
    const value = parseFloat(cleanStr.replace(/[^\d.-]/g, ''));
    if (isNaN(value)) return 0;
    
    const lower = cleanStr.toLowerCase();
    if (lower.includes('tib') || lower.includes('tb') || lower.includes('to')) return value * 1024;
    if (lower.includes('gib') || lower.includes('gb') || lower.includes('go')) return value;
    if (lower.includes('mib') || lower.includes('mb') || lower.includes('mo')) return value / 1024;
    if (lower.includes('kib') || lower.includes('kb') || lower.includes('ko')) return value / (1024 * 1024);
    return value;
  };

  // Extract data for the specific tracker
  const data = history
    .filter((entry) => entry[trackerName])
    .map((entry) => {
      const stats = entry[trackerName] as TrackerData;
      // @ts-ignore
      const timestamp = entry._timestamp ? new Date(entry._timestamp * 1000).getTime() : new Date().getTime();
      
      let val = 0;
      if (stats && typeof stats === 'object' && 'ratio' in stats) {
        if (metric === 'ratio' && stats.ratio) {
             val = parseFloat(stats.ratio.replace(',', '.').replace(/[^\d.-]/g, ''));
        } else if (metric === 'buffer') {
             // Unit3D uses 'buffer', Sharewood uses 'dl_capacity' (mapped to buffer in UI but raw in JSON?)
             // In JSON, Sharewood has 'dl_capacity'. Unit3D has 'buffer'.
             // Let's check the raw JSON structure or the types.
             // The types say: Unit3D has buffer, Sharewood has dl_capacity.
             // But wait, the scraper saves them with those keys.
             // Let's try to find either.
             // @ts-ignore
             const rawBuffer = stats.buffer || stats.dl_capacity || "0";
             val = parseSize(rawBuffer);
        }
      }

      return {
        x: timestamp,
        y: val,
      };
    });

  const series = [
    {
      name: metric === 'ratio' ? "Ratio" : "Buffer (GB)",
      data: data,
    },
  ];

  const options: ApexOptions = {
    theme: {
      mode: theme,
    },
    legend: {
      show: false,
      position: "top",
      horizontalAlign: "left",
    },
    colors: ["#3C50E0", "#80CAEE"],
    chart: {
      fontFamily: "Satoshi, sans-serif",
      height: 335,
      type: "area",
      background: 'transparent',
      dropShadow: {
        enabled: true,
        color: "#623CEA14",
        top: 10,
        blur: 4,
        left: 0,
        opacity: 0.1,
      },
      toolbar: {
        show: false,
      },
    },
    responsive: [
      {
        breakpoint: 1024,
        options: {
          chart: {
            height: 300,
          },
        },
      },
      {
        breakpoint: 1366,
        options: {
          chart: {
            height: 350,
          },
        },
      },
    ],
    stroke: {
      width: [2, 2],
      curve: "straight",
    },
    grid: {
      borderColor: theme === 'dark' ? '#374151' : '#E2E8F0',
      xaxis: {
        lines: {
          show: true,
        },
      },
      yaxis: {
        lines: {
          show: true,
        },
      },
    },
    dataLabels: {
      enabled: false,
    },
    markers: {
      size: 4,
      colors: "#fff",
      strokeColors: ["#3056D3", "#80CAEE"],
      strokeWidth: 3,
      strokeOpacity: 0.9,
      strokeDashArray: 0,
      fillOpacity: 1,
      discrete: [],
      hover: {
        size: undefined,
        sizeOffset: 5,
      },
    },
    xaxis: {
      type: "datetime",
      axisBorder: {
        show: false,
      },
      axisTicks: {
        show: false,
      },
      labels: {
        style: {
          colors: theme === 'dark' ? '#9CA3AF' : '#64748B',
        },
      },
      tooltip: {
        enabled: false,
      },
    },
    yaxis: {
      labels: {
        style: {
          colors: theme === 'dark' ? '#9CA3AF' : '#64748B',
        },
      },
      title: {
        style: {
          fontSize: "0px",
        },
      },
      min: 0,
    },
    tooltip: {
      x: {
        format: 'dd MMM yyyy HH:mm',
      },
    },
  };

  return (
    <div className="col-span-12 rounded-sm border border-stroke bg-white px-5 pt-7.5 pb-5 shadow-default dark:border-strokedark dark:bg-boxdark sm:px-7.5 xl:col-span-8">
      <div className="flex flex-wrap items-center justify-between gap-3 sm:flex-nowrap mb-4">
        <div className="flex w-full flex-wrap gap-3 sm:gap-5">
          <div className="flex min-w-47.5">
            <span className="mt-1 mr-2 flex h-4 w-full max-w-4 items-center justify-center rounded-full border border-primary">
              <span className="block h-2.5 w-full max-w-2.5 rounded-full bg-primary"></span>
            </span>
            <div className="w-full">
              <p className="font-semibold text-primary">{trackerName}</p>
            </div>
          </div>
        </div>
        
        <div className="flex items-center space-x-2 bg-gray-100 dark:bg-meta-4 rounded-md p-1">
            <button 
                onClick={() => setMetric('ratio')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${metric === 'ratio' ? 'bg-white dark:bg-boxdark shadow-sm text-black dark:text-white' : 'text-gray-500 hover:text-black dark:hover:text-white'}`}
            >
                Ratio
            </button>
            <button 
                onClick={() => setMetric('buffer')}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${metric === 'buffer' ? 'bg-white dark:bg-boxdark shadow-sm text-black dark:text-white' : 'text-gray-500 hover:text-black dark:hover:text-white'}`}
            >
                Buffer
            </button>
        </div>
      </div>

      <div>
        <div id="chartOne" className="-ml-5">
          <ReactApexChart
            options={options}
            series={series}
            type="area"
            height={350}
          />
        </div>
      </div>
    </div>
  );
};

export default TrackerChart;
