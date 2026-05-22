/**
 * Angular imports.
 */
import { Component, OnDestroy } from '@angular/core';

/**
 * Services imports.
 */
import { DescriptorService, DEFAULT_REGION } from '../../../@core/services';
import { ChartService, RegionFilterService } from '../../../@core/services';

/**
 * Interfaces imports.
 */
import { Descriptor, DirtyType } from '@core/interfaces';
import { RegionFilter } from '@core/interfaces';

/**
 * Rxjs imports.
 */
import { Subscription } from 'rxjs';

@Component({
  standalone: false,
  selector: 'app-statistics-sidebar',
  templateUrl: './statistics-sidebar.component.html',
  styleUrls: ['./statistics-sidebar.component.scss'],
})
class StatisticsSidebarComponent implements OnDestroy {

  private descriptorSubscription: Subscription = new Subscription();
  private regionFilterSubscription: Subscription = new Subscription();

  public summaryKeys: string[] = [
    'coverage_natural',
    'coverage_comparison_app',
    'coverage_comparison_rl',
    'coverage_comparison_mfa',
  ];

  public summaryData: Map<string, any> = new Map<string, any>();

  public coverageNaturalChartData: any = null;
  public coverageComparisonAppChartData: any = null;
  public coverageComparisonRlChartData: any = null;
  public coverageComparisonMfaChartData: any = null;

  public stackedBarOptions: any = {
    indexAxis: 'y',
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          usePointStyle: true,
          pointStyle: 'circle',
          padding: 15,
          font: {
            size: 11
          }
        }
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        axis: 'y',
        callbacks: {
          label: (context: any) => {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.x !== null) {
              label += new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(context.parsed.x) + ' %';
            }
            return label;
          }
        }
      }
    },
    scales: {
      x: {
        stacked: true,
        max: 100,
        grid: {
          display: false
        },
        ticks: {
          callback: (value: any) => {
            return value + '%';
          }
        }
      },
      y: {
        stacked: true,
        grid: {
          display: false
        }
      }
    },
    maintainAspectRatio: false,
    hover: {
      mode: 'index',
      intersect: false,
      axis: 'y'
    }
  };

  public doughnutOptions: any = {
    plugins: {
      legend: {
        display: true,
        position: 'bottom',
        labels: {
          usePointStyle: true,
          pointStyle: 'circle',
          padding: 20,
          font: {
            size: 12,
            weight: '500'
          },
          color: '#495057'
        }
      },
      tooltip: {
        enabled: true,
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleFont: {
          size: 14,
          weight: 'bold'
        },
        bodyFont: {
          size: 13
        },
        padding: 10,
        cornerRadius: 4,
        displayColors: true,
        callbacks: {
          label: (context: any) => {
            let label = context.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed !== null) {
              const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
              const percent = ((context.parsed / total) * 100).toFixed(2) + '%';
              label += new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(context.parsed) + ' ha (' + percent + ')';
            }
            return label;
          }
        }
      }
    },
    animation: {
      animateRotate: true,
      animateScale: true,
      duration: 1000,
      easing: 'easeOutQuart'
    },
    maintainAspectRatio: false,
    cutout: '65%',
    hover: {
      mode: 'nearest',
      intersect: true
    }
  };

  public layersForStatistics: any = {};

  public regionFilter: RegionFilter = DEFAULT_REGION;

  constructor(
    private descriptorService: DescriptorService,
    private regionFilterService: RegionFilterService,
    private chartService: ChartService
  ) {
    this.regionFilterSubscription.add(
      this.regionFilterService.getRegionFilter().subscribe({
        next: (regionFilter: RegionFilter) => {
          this.regionFilter = regionFilter;

          this.getAllSummaryData();
        },
      })
    );

    this.descriptorSubscription.add(
      this.descriptorService
        .getDescriptor()
        .subscribe((descriptor: Descriptor | null) => {
          if (descriptor === null) return;

          this.updateLayersForStatistics(descriptor);
        })
    );
  }

  ngOnDestroy(): void {
    this.descriptorSubscription.unsubscribe();
    this.regionFilterSubscription.unsubscribe();
  }

  private updateLayersForStatistics(descriptor: Descriptor): void {
    let dirtyBit = descriptor.dirtyBit;

    Object.keys(this.layersForStatistics).forEach((summaryKey: string) => {
      if (this.layersForStatistics[summaryKey].layer !== dirtyBit.layer) return;

      let descriptorLayer = this.descriptorService.getLayer(dirtyBit.layer!);

      switch (dirtyBit.dirty) {
        case DirtyType.VISIBILITY:
          this.layersForStatistics[summaryKey].switch = descriptorLayer.visible;
          break;
        case DirtyType.SOURCE:
          let year = parseInt(descriptorLayer.selectedTypeObject?.filterSelected?.split('=')[1]!);

          this.layersForStatistics[summaryKey].year = year;

          this.getLayerSummaryData(summaryKey);
          break;
      }
    });
  }

  private getAllSummaryData(): void {
    this.summaryKeys.forEach((key: string) => {
      this.getLayerSummaryData(key);
    });
  }

  private getLayerSummaryData(summaryKey: string): void {
    let year: any = '2023';

    if (this.layersForStatistics[summaryKey]) {
      year = this.layersForStatistics[summaryKey].year;
    }

    this.chartService
      .getSummary(summaryKey, this.regionFilter, year)
      .subscribe({
        next: (summary: any) => {
          this.summaryData.set(summaryKey, {
            data: summary,
            year: year,
          });

          this.updateChartData(summaryKey);
        },
        error: (error) => {
          console.error(error);
        },
      });
  }

  private updateChartData(key: string): void {
    if (key === 'coverage_natural') {
      const summary = this.summaryData.get('coverage_natural');
      if (!summary || !summary.data || !Array.isArray(summary.data)) {
        this.coverageNaturalChartData = null;
        return;
      }

      const labels = summary.data.map((item: any) => item.label);
      const data = summary.data.map((item: any) => item.value);
      const backgroundColor = summary.data.map((item: any) => item.color);

      this.coverageNaturalChartData = {
        labels: labels,
        datasets: [
          {
            data: data,
            backgroundColor: backgroundColor,
            hoverBackgroundColor: backgroundColor,
            borderWidth: 2,
            borderColor: '#ffffff',
            hoverOffset: 20
          }
        ]
      };
    } else if (key === 'coverage_comparison_app' || key === 'coverage_comparison_rl' || key === 'coverage_comparison_mfa') {
      const summary = this.summaryData.get(key);
      if (!summary || !summary.data || !Array.isArray(summary.data)) {
        if (key === 'coverage_comparison_app') this.coverageComparisonAppChartData = null;
        else if (key === 'coverage_comparison_rl') this.coverageComparisonRlChartData = null;
        else this.coverageComparisonMfaChartData = null;
        return;
      }

      const rawData = summary.data;
      
      const totalAreaPerLabel = new Map<string, number>();
      rawData.forEach((item: any) => {
        const current = totalAreaPerLabel.get(item.label) || 0;
        totalAreaPerLabel.set(item.label, current + item.value);
      });

      const sortedLabels = Array.from(totalAreaPerLabel.entries())
        .sort((a, b) => b[1] - a[1])
        .map(entry => entry[0]);

      const classesMap = new Map<string, string>();
      rawData.forEach((item: any) => {
        if (!classesMap.has(item.classe)) {
          classesMap.set(item.classe, item.color);
        }
      });

      const datasets = Array.from(classesMap.entries()).map(([classe, color]) => {
        const data = sortedLabels.map(label => {
          const found = rawData.find((item: any) => item.label === label && item.classe === classe);
          const totalArea = totalAreaPerLabel.get(label) || 1;
          return found ? (found.value / totalArea) * 100 : 0;
        });

        return {
          label: classe,
          data: data,
          backgroundColor: color,
          hoverBackgroundColor: color
        };
      });

      const chartData = {
        labels: sortedLabels,
        datasets: datasets
      };

      if (key === 'coverage_comparison_app') this.coverageComparisonAppChartData = chartData;
      else if (key === 'coverage_comparison_rl') this.coverageComparisonRlChartData = chartData;
      else this.coverageComparisonMfaChartData = chartData;
    }
  }

}

export { StatisticsSidebarComponent };
