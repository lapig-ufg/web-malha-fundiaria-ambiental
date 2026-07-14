/**
 * Angular imports.
 */
import { Component, OnDestroy } from '@angular/core';
import { DecimalPipe } from '@angular/common';

/**
 * Services imports.
 */
import { DescriptorService, DEFAULT_REGION } from '../../../@core/services';
import { ChartService, RegionFilterService } from '../../../@core/services';
import { LocalizationService } from '@core/internationalization/localization.service';
import { SelectedFeatureService, SelectedFeature } from '../../../@core/services';
import { ZonalService } from '../../../@core/services';

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
    'property_count',
    'coverage_natural',
    'coverage_comparison_app',
    'coverage_comparison_rl',
    'coverage_comparison_mfa',
  ];

  public summaryData: Map<string, any> = new Map<string, any>();

  public propertyCount: number | null = null;

  public coverageNaturalChartData: any = null;
  public coverageComparisonAppChartData: any = null;
  public coverageComparisonRlChartData: any = null;
  public coverageComparisonMfaChartData: any = null;

  /**
   * Vegetation evolution bar chart data (region-level):
   * x = year, y = percentage of natural vegetation (class_1 / (class_1 + class_2) * 100).
   * Populated via the /service/charts/vegetation-evolution endpoint (separate from resumo
   * so that a missing table doesn't break the other summary cards).
   */
  public vegetationEvolutionChartData: any = null;

  /**
   * Vegetation evolution per categoria (region-level): same shape as
   * vegetationEvolutionChartData, but scoped to rows where
   * categoria = 'Área de preservação permanente' (APP) / 'Reserva Legal' (RL),
   * sourced from natural_vegetation_regions_app_rl_1985_2024 via the
   * /service/charts/vegetation-evolution-by-categoria endpoint.
   */
  public vegetationEvolutionAppChartData: any = null;
  public vegetationEvolutionRlChartData: any = null;
  public vegetationEvolutionAppLoading = false;
  public vegetationEvolutionRlLoading = false;

  /**
   * Per-property vegetation chart (bar): x = year, y = % of the property
   * area classified as natural vegetation. Populated by polling the
   * /service/zonal/jobs endpoint whenever a malha_fundiaria feature is
   * selected on the map.
   */
  public malhaVegetationChartData: any = null;
  public malhaAppChartData: any = null;
  public malhaRlChartData: any = null;
  public malhaVegetationLoading: boolean = false;
  public currentJobId: string | null = null;
  private selectedFeatureSubscription: Subscription = new Subscription();

  /**
   * True when the sidebar is showing the per-property (malha_fundiaria)
   * panel — the two region-based charts and the description are hidden
   * in this mode; the property attributes + vegetation chart are shown.
   */
  public malhaMode: boolean = false;
  public malhaFeature: SelectedFeature | null = null;

  public malhaBarOptions: any = {
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context: any) =>
            `${Number(context.parsed.y).toFixed(2)}%`,
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: (value: any) => value + '%',
        },
      },
    },
    maintainAspectRatio: false,
  };

  public vegetationBarOptions: any = {
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context: any) =>
            `${Number(context.parsed.y).toFixed(2)}%`,
        },
      },
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Ano',
        },
      },
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          stepSize: 20,
          callback: (value: any) => value + '%',
        },
        title: {
          display: true,
          text: '% Vegetação Natural',
        },
      },
    },
    maintainAspectRatio: false,
  };

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

  /**
   * Dynamic title for the natural-coverage accordion tab. Returns the
   * country-specific string when the region is Brazil, otherwise
   * interpolates the current region name (state, municipality, biome).
   */
  public get coverageNaturalTitle(): string {
    if (this.regionFilter.type === 'country') {
      return this.localizationService.translate(
        'right_sidebar.resumo_card.coverage_natural_title_country',
      );
    }
    return this.localizationService.translate(
      'right_sidebar.resumo_card.coverage_natural_title_region',
      { region: this.regionFilter.text },
    );
  }

  /**
   * Dynamic title for the vegetation evolution accordion tab.
   * Shows a country-specific string when the region is Brazil,
   * otherwise interpolates the current region name.
   */
  public get vegetationEvolutionTitle(): string {
    if (this.regionFilter.type === 'country') {
      return this.localizationService.translate(
        'right_sidebar.resumo_card.vegetation_evolution_title_country',
      );
    }
    return this.localizationService.translate(
      'right_sidebar.resumo_card.vegetation_evolution_title_region',
      { region: this.regionFilter.text },
    );
  }

  constructor(
    private descriptorService: DescriptorService,
    private regionFilterService: RegionFilterService,
    private chartService: ChartService,
    private localizationService: LocalizationService,
    private selectedFeatureService: SelectedFeatureService,
    private zonalService: ZonalService,
    private decimalPipe: DecimalPipe,
  ) {
    this.regionFilterSubscription.add(
      this.regionFilterService.getRegionFilter().subscribe({
        next: (regionFilter: RegionFilter) => {
          this.regionFilter = regionFilter;

          this.getAllSummaryData();
        },
      })
    );

    this.regionFilterSubscription.add(
      this.localizationService.translateService.onLangChange.subscribe(() => {
        this.getAllSummaryData();
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

    // Subscribe to the currently-selected map feature. Whenever a
    // malha_fundiaria feature is picked (by map click or CAR search) we
    // enter "malha mode" and kick off a zonal job to render the
    // vegetation bar chart; otherwise we return to the region mode
    // (two main charts + description).
    this.selectedFeatureSubscription.add(
      this.selectedFeatureService.getSelectedFeature().subscribe({
        next: (feature: SelectedFeature | null) => {
          if (!feature || feature.idLayer !== 'malha_fundiaria_ambiental') {
            this.malhaMode = false;
            this.malhaFeature = null;
            this.clearMalhaChart();
            return;
          }
          this.malhaMode = true;
          this.malhaFeature = feature;
          this.loadMalhaChart(feature);
        },
      })
    );
  }

  ngOnDestroy(): void {
    this.descriptorSubscription.unsubscribe();
    this.regionFilterSubscription.unsubscribe();
    this.selectedFeatureSubscription.unsubscribe();
  }

  /**
   * Format an attribute value for display. Mirrors the logic used by the
   * map popup (general-map.component.ts:getAttributeValue): integers
   * are rounded, decimals are formatted with 2 fraction digits, and
   * strings/dates are passed through.
   */
  public getAttributeValue(type: any, value: any): string {
    if (value === null || value === undefined || value === '') return '';

    const lang = this.localizationService.currentLang();
    const locale = lang === 'pt' ? 'pt-BR' : 'en-US';

    let columnType = type;
    if (typeof type === 'object' && type !== null) {
      columnType = type.columnType;
    }

    const numValue =
      typeof value === 'string' && value.trim() !== ''
        ? Number(value.replace(',', '.'))
        : value;
    const isNumeric = typeof numValue === 'number' && !isNaN(numValue);

    if (isNumeric && columnType !== 'integer') {
      return this.decimalPipe.transform(numValue, '1.0-2', locale) || String(value);
    }

    switch (columnType) {
      case 'integer':
        return this.decimalPipe.transform(numValue, '1.0-0', locale) || String(value);
      case 'date':
      case 'string':
      default:
        return String(value);
    }
  }

  private clearMalhaChart(): void {
    this.malhaVegetationChartData = null;
    this.malhaAppChartData = null;
    this.malhaRlChartData = null;
    this.malhaVegetationLoading = false;
    this.currentJobId = null;
  }

  private loadMalhaChart(feature: SelectedFeature): void {
    this.malhaVegetationLoading = true;
    this.malhaVegetationChartData = null;
    this.malhaAppChartData = null;
    this.malhaRlChartData = null;
    this.currentJobId = null;

    this.zonalService.startZonalJob(feature.geometry).subscribe({
      next: (resp) => {
        this.currentJobId = resp.job_id;
        this.pollJobUntilDone(resp.job_id);
      },
      error: (err) => {
        console.error('startZonalJob failed', err);
        this.malhaVegetationLoading = false;
      },
    });
  }

  private pollJobUntilDone(jobId: string): void {
    // Poll every 1.5s; bail out if the user changed selection in the
    // meantime (the in-flight guard).
    const tick = (): void => {
      if (this.currentJobId !== jobId) return;

      this.zonalService.pollZonalJob(jobId).subscribe({
        next: (resp) => {
          if (this.currentJobId !== jobId) return;

          if (resp.status === 'pending') {
            setTimeout(tick, 1500);
            return;
          }
          if (resp.status === 'error') {
            console.error('zonal job error', resp.error);
            this.malhaVegetationLoading = false;
            return;
          }
          this.buildAllMalhaCharts(resp.result || {});
          this.malhaVegetationLoading = false;
        },
        error: (err) => {
          console.error('poll failed', err);
          this.malhaVegetationLoading = false;
        },
      });
    };
    setTimeout(tick, 800);
  }

  /**
   * Build a Chart.js bar-chart dataset from an array of per-year rows.
   * Each row must have `ano` and the given valueKey.
   */
  private buildZoneBarChartData(rows: any[], valueKey: string): any {
    const sorted = [...rows].sort(
      (a, b) => (a.ano ?? 0) - (b.ano ?? 0),
    );
    const labels = sorted.map((r) =>
      r.ano != null ? String(r.ano) : '',
    );
    const data = sorted.map((r) =>
      Number(Number(r[valueKey] ?? 0).toFixed(2)),
    );
    return {
      labels,
      datasets: [
        {
          label: this.localizationService.translate(
            'right_sidebar.malha_chart.label_pct_natural',
          ),
          data,
          backgroundColor: '#2e8b57',
          borderColor: '#1f5e3a',
          borderWidth: 1,
        },
      ],
    };
  }

  /**
   * Build all three malha-mode charts from the v2 zonal result dict.
   * The result has keys propriedade, app, rl — each an array of per-year rows
   * with fields ano, pct_natural, area_natural_ha, etc.
   */
  private buildAllMalhaCharts(result: any): void {
    // Propriedade (whole property) — always present
    if (result.propriedade && Array.isArray(result.propriedade)) {
      this.malhaVegetationChartData = this.buildZoneBarChartData(
        result.propriedade,
        'pct_natural',
      );
    }

    // APP zone
    if (result.app && Array.isArray(result.app)) {
      this.malhaAppChartData = this.buildZoneBarChartData(
        result.app,
        'pct_natural',
      );
    }

    // RL zone
    if (result.rl && Array.isArray(result.rl)) {
      this.malhaRlChartData = this.buildZoneBarChartData(
        result.rl,
        'pct_natural',
      );
    }
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
    this.getVegetationEvolutionData();
    this.getVegetationEvolutionAppData();
    this.getVegetationEvolutionRlData();
  }

  /**
   * Fetch vegetation evolution data from the separate endpoint
   * so that a missing table doesn't break the other summary cards.
   */
  private getVegetationEvolutionData(): void {
    this.chartService
      .getVegetationEvolution(this.regionFilter)
      .subscribe({
        next: (data: any) => {
          if (Array.isArray(data) && data.length > 0) {
            this.summaryData.set('vegetation_evolution', {
              data: data,
              year: null,
            });
            this.updateChartData('vegetation_evolution');
          } else {
            this.vegetationEvolutionChartData = null;
          }
        },
        error: (error) => {
          console.error('Vegetation evolution data unavailable:', error);
          this.vegetationEvolutionChartData = null;
        },
      });
  }

  /**
   * Fetch vegetation evolution scoped to a categoria (APP / RL) from the
   * by-categoria endpoint. Same resilient pattern as the total evolution.
   */
  private getVegetationEvolutionByCategoriaData(
    categoria: string,
    summaryKey: 'vegetation_evolution_app' | 'vegetation_evolution_rl',
  ): void {
    const isApp = summaryKey === 'vegetation_evolution_app';
    if (isApp) {
      this.vegetationEvolutionAppLoading = true;
    } else {
      this.vegetationEvolutionRlLoading = true;
    }

    this.chartService
      .getVegetationEvolutionByCategoria(this.regionFilter, categoria)
      .subscribe({
        next: (data: any) => {
          if (isApp) {
            this.vegetationEvolutionAppLoading = false;
          } else {
            this.vegetationEvolutionRlLoading = false;
          }
          if (Array.isArray(data) && data.length > 0) {
            this.summaryData.set(summaryKey, { data: data, year: null });
            this.updateChartData(summaryKey);
          } else {
            if (isApp) {
              this.vegetationEvolutionAppChartData = null;
            } else {
              this.vegetationEvolutionRlChartData = null;
            }
          }
        },
        error: (error) => {
          console.error(`Vegetation evolution (${summaryKey}) data unavailable:`, error);
          if (isApp) {
            this.vegetationEvolutionAppLoading = false;
            this.vegetationEvolutionAppChartData = null;
          } else {
            this.vegetationEvolutionRlLoading = false;
            this.vegetationEvolutionRlChartData = null;
          }
        },
      });
  }

  private getVegetationEvolutionAppData(): void {
    this.getVegetationEvolutionByCategoriaData(
      'Área de preservação permanente',
      'vegetation_evolution_app',
    );
  }

  private getVegetationEvolutionRlData(): void {
    this.getVegetationEvolutionByCategoriaData('Reserva Legal', 'vegetation_evolution_rl');
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

  private labelMap: any = {
    'app': 'app',
    'rl': 'rl',
    'mfa': 'mfa',
    'natural': 'natural',
    'non_natural': 'non_natural',
    'Áreas de Preservação Permanente': 'app',
    'Reserva Legal': 'rl',
    'Reserva_Legal': 'rl',
    'Malha Fundiária': 'mfa',
    'Natural': 'natural',
    'Não Natural': 'non_natural'
  };

  private updateChartData(key: string): void {
    if (key === 'property_count') {
      const summary = this.summaryData.get('property_count');
      if (summary && summary.data && summary.data.property_count !== undefined) {
        this.propertyCount = summary.data.property_count;
      } else {
        this.propertyCount = null;
      }
      return;
    }
    if (key === 'coverage_natural') {
      const summary = this.summaryData.get('coverage_natural');
      if (!summary || !summary.data || !Array.isArray(summary.data)) {
        this.coverageNaturalChartData = null;
        return;
      }

      const labels = summary.data.map((item: any) => {
        const labelKey = this.labelMap[item.label] || item.label;
        return this.localizationService.translate('right_sidebar.resumo_card.chart_labels.' + labelKey);
      });
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
          label: this.localizationService.translate('right_sidebar.resumo_card.chart_labels.' + (this.labelMap[classe] || classe)),
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
    } else if (key === 'vegetation_evolution') {
      const summary = this.summaryData.get('vegetation_evolution');
      if (!summary || !summary.data || !Array.isArray(summary.data)) {
        this.vegetationEvolutionChartData = null;
        return;
      }

      const rawData = summary.data;
      const labels = rawData.map((item: any) => String(item.label));
      const data = rawData.map((item: any) => Number(Number(item.value).toFixed(2)));
      const color = rawData.length > 0 ? rawData[0].color : '#228B22';

      this.vegetationEvolutionChartData = {
        labels,
        datasets: [
          {
            label: this.localizationService.translate(
              'right_sidebar.resumo_card.chart_labels.vegetation_pct',
            ),
            data,
            backgroundColor: color,
            borderColor: '#1f5e3a',
            borderWidth: 1,
          },
        ],
      };

      this.vegetationBarOptions.scales.x.title.text =
        this.localizationService.translate('right_sidebar.resumo_card.vegetation_evolution_x_axis') || 'Ano';
      this.vegetationBarOptions.scales.y.title.text =
        this.localizationService.translate('right_sidebar.resumo_card.vegetation_evolution_y_axis') || '% Vegetação Natural';
    } else if (key === 'vegetation_evolution_app' || key === 'vegetation_evolution_rl') {
      const summary = this.summaryData.get(key);
      const isApp = key === 'vegetation_evolution_app';
      if (!summary || !summary.data || !Array.isArray(summary.data)) {
        if (isApp) {
          this.vegetationEvolutionAppChartData = null;
        } else {
          this.vegetationEvolutionRlChartData = null;
        }
        return;
      }

      const rawData = summary.data;
      const labels = rawData.map((item: any) => String(item.label));
      const data = rawData.map((item: any) => Number(Number(item.value ?? 0).toFixed(2)));
      const color = rawData.length > 0 ? rawData[0].color : '#228B22';

      const chartData = {
        labels,
        datasets: [
          {
            label: this.localizationService.translate(
              'right_sidebar.resumo_card.chart_labels.vegetation_pct',
            ),
            data,
            backgroundColor: color,
            borderColor: '#1f5e3a',
            borderWidth: 1,
          },
        ],
      };

      if (isApp) {
        this.vegetationEvolutionAppChartData = chartData;
      } else {
        this.vegetationEvolutionRlChartData = chartData;
      }

      // Reuse the same axis titles as the total vegetation graph.
      this.vegetationBarOptions.scales.x.title.text =
        this.localizationService.translate('right_sidebar.resumo_card.vegetation_evolution_x_axis') || 'Ano';
      this.vegetationBarOptions.scales.y.title.text =
        this.localizationService.translate('right_sidebar.resumo_card.vegetation_evolution_y_axis') || '% Vegetação Natural';
    }
  }

}

export { StatisticsSidebarComponent };
