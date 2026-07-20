/**
 * Angular imports.
 */
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

/**
 * Rxjs imports.
 */
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

/**
 * Interfaces imports.
 */
import { RegionFilter } from '@core/interfaces';
import { LocalizationService } from '@core/internationalization/localization.service';

@Injectable({
  providedIn: 'root',
})
class StatisticsService {
  private apiURL = '/service/charts';

  httpOptions = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json',
    }),
  };

  constructor(
    private httpClient: HttpClient,
    private localizationService: LocalizationService
  ) {}

  /**
   * Get StatisticsSidebar charts.
   * @param chart Chart name.
   * @param regionFilter
   * @param year
   * @returns
   */
  public getSummary(chart: string, regionFilter: RegionFilter, year: string): Observable<any> {
    let params: string =
      `lang=${this.localizationService.currentLang()}` +
      `&typeRegion=${regionFilter.type}` +
      `&valueRegion=${regionFilter.value}` +
      `&textRegion=${regionFilter.text}` +
      `&card_resume=${chart}` +
      `&year=${year}`;

    return this.httpClient
      .get<any>(`${this.apiURL}/resumo?${params}`, this.httpOptions)
      .pipe(map((response) => response))
      .pipe(catchError(this.errorHandler));
  }

  /**
   * Get pasture graphs.
   * @param regionFilter
   * @returns
   */
  public getPastureGraph(regionFilter: RegionFilter): Observable<any> {
    let params =
      `lang=${this.localizationService.currentLang()}` +
      `&typeRegion=${regionFilter.type}` +
      `&valueRegion=${regionFilter.value}` +
      `&textRegion=${regionFilter.text}`;

    return this.httpClient
      .get<any>(`${this.apiURL}/pastureGraph?${params}`, this.httpOptions)
      .pipe(catchError(this.errorHandler));
  }

  /**
   * Get vegetation evolution chart data (year vs % natural vegetation).
   * Uses a separate endpoint so failures don't affect other summary data.
   * @param regionFilter
   * @returns
   */
  public getVegetationEvolution(regionFilter: RegionFilter): Observable<any> {
    let params =
      `lang=${this.localizationService.currentLang()}` +
      `&typeRegion=${regionFilter.type}` +
      `&valueRegion=${regionFilter.value}` +
      `&textRegion=${regionFilter.text}`;

    return this.httpClient
      .get<any>(`${this.apiURL}/vegetation-evolution?${params}`, this.httpOptions)
      .pipe(catchError(this.errorHandler));
  }

  /**
   * Get vegetation evolution chart data (year vs % natural vegetation)
   * scoped to a given categoria ('Área de preservação permanente' or
   * 'Reserva Legal'), sourced from natural_vegetation_regions_app_rl_1985_2024.
   * @param regionFilter
   * @param categoria
   * @returns
   */
  public getVegetationEvolutionByCategoria(regionFilter: RegionFilter, categoria: string): Observable<any> {
    const params =
      `lang=${this.localizationService.currentLang()}` +
      `&typeRegion=${regionFilter.type}` +
      `&valueRegion=${regionFilter.value}` +
      `&textRegion=${regionFilter.text}` +
      `&categoria=${encodeURIComponent(categoria)}`;

    return this.httpClient
      .get<any>(`${this.apiURL}/vegetation-evolution-by-categoria?${params}`, this.httpOptions)
      .pipe(catchError(this.errorHandler));
  }

  /**
   * Get forest surplus chart data (year vs area, ha): natural vegetation
   * area of the analysis area (natural_vegetation_regions.class_1) minus
   * the natural vegetation area within APP + Reserva Legal
   * (natural_vegetation_regions_app_rl_1985_2024.class_1).
   * @param regionFilter
   * @returns
   */
  public getForestSurplus(regionFilter: RegionFilter): Observable<any> {
    let params =
      `lang=${this.localizationService.currentLang()}` +
      `&typeRegion=${regionFilter.type}` +
      `&valueRegion=${regionFilter.value}` +
      `&textRegion=${regionFilter.text}`;

    return this.httpClient
      .get<any>(`${this.apiURL}/forest-surplus?${params}`, this.httpOptions)
      .pipe(catchError(this.errorHandler));
  }

  private errorHandler(error: any) {
    let errorMessage = '';
    if (error.error instanceof ErrorEvent) {
      errorMessage = error.error.message;
    } else {
      errorMessage = `Error Code: ${error.status}\nMessage: ${error.message}`;
    }
    return throwError(errorMessage);
  }
}

export { StatisticsService as ChartService };
