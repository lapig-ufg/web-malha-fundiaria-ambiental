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

const API_URL = '/service/zonal';

@Injectable({
  providedIn: 'root',
})
class ZonalService {
  httpOptions = {
    headers: new HttpHeaders({
      'Content-Type': 'application/json',
    }),
  };

  constructor(private httpClient: HttpClient) {}

  /**
   * Start a per-property zonal statistics job.
   * Returns 202 + {job_id} from the server.
   */
  public startZonalJob(
    geometry: any,
    classeVegetacao: number = 1,
    inputCrs: string = 'EPSG:4326',
  ): Observable<{ job_id: string }> {
    return this.httpClient
      .post<{ job_id: string }>(
        `${API_URL}/jobs`,
        { geometry, classe_vegetacao: classeVegetacao, input_crs: inputCrs },
        this.httpOptions,
      )
      .pipe(map((response) => response))
      .pipe(catchError(this.errorHandler));
  }

  /**
   * Poll a previously-started zonal job.
   * Returns 200 with {status, result?, error?}.
   */
  public pollZonalJob(
    jobId: string,
  ): Observable<{ status: string; result?: any[]; error?: string }> {
    return this.httpClient
      .get<{ status: string; result?: any[]; error?: string }>(
        `${API_URL}/jobs/${jobId}`,
      )
      .pipe(map((response) => response))
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

export { ZonalService };
