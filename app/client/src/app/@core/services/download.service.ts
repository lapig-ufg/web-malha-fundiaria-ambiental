import { Injectable } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import { catchError, map } from 'rxjs/operators';
import { RegionFilterService } from './region-filter.service';
import { DescriptorType, RegionFilter } from '@core/interfaces';

const IBGE_TO_STATE: { [prefix: string]: string } = {
  '12': 'AC', '27': 'AL', '16': 'AP', '13': 'AM', '29': 'BA',
  '23': 'CE', '53': 'DF', '32': 'ES', '52': 'GO', '21': 'MA',
  '31': 'MG', '51': 'MT', '50': 'MS', '14': 'RR', '22': 'PI',
  '41': 'PR', '24': 'RN', '43': 'RS', '11': 'RO', '33': 'RJ',
  '15': 'PA', '25': 'PB', '26': 'PE', '28': 'SE', '35': 'SP',
  '42': 'SC', '44': 'TO',
};

export { DownloadService };

@Injectable({
  providedIn: 'root',
})
class DownloadService {
  private apiURL = `${environment.OWS}/api/download`;
  private apiS3 = `${environment.LAPIG_DOWNLOAD_API}/api/download/`;

  constructor(
    private httpClient: HttpClient,
    private regionFilterService: RegionFilterService
  ) {}

  private resolveRegionCode(filter: RegionFilter): string {
    switch (filter.type) {
      case 'state':
        return filter.value;
      case 'city': {
        const prefix = filter.value.substring(0, 2);
        return IBGE_TO_STATE[prefix] || '';
      }
      default:
        return '';
    }
  }

  // TODO: Trazer o ErroMessageService para dentro do download.
  public downloadGeoFile(descriptorType: DescriptorType, fileType: string): Observable<any> {
    let formatUrl = descriptorType.download.urls?.[fileType];

    if (formatUrl && formatUrl.includes('{region}')) {
      const regionCode = this.resolveRegionCode(this.regionFilterService.currentFilter);
      formatUrl = formatUrl.replace('{region}', regionCode);
    }

    if (formatUrl) {
      window.open(formatUrl, '_blank');
      return of({ status: 'success' });
    }

    if (descriptorType.download.url) {
      window.open(descriptorType.download.url, '_blank');
      return of({ status: 'success' });
    }

    let regionFilter = this.regionFilterService.currentFilter;

    let params = {
      layer: descriptorType,
      region: regionFilter,
      filter: descriptorType.filters?.filter((filter) => descriptorType.filterSelected === filter.valueFilter)[0],
      typeDownload: fileType,
    };

    return this.httpClient.post(this.apiS3, params).pipe(
      map((response: any) => {
        if (response == null) throw new Error('Erro');

        window.open(response.url, '_blank');

        return {status: 'success'}
      })
    ).pipe(
      catchError(error => this.errorHandlerS3(error)));
  }

  public downloadRequest(parameters: any): Observable<Blob> {
    return this.httpClient.post(this.apiURL, parameters, {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS,DELETE,PUT',
      }),
      responseType: 'blob',
    });
  }

  public downloadRequestSLD(layer: any): Observable<Blob> {
    const url = `${environment.OWS}/ows?request=GetStyles&layers=${layer}&service=wms&version=1.1.1`;

    return this.httpClient.get(url, {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS,DELETE,PUT',
      }),
      responseType: 'blob',
    });
  }

  private errorHandlerS3(error: any) {
    const error_types = ['unable_filter_layer', 'file_empty', 'file_not_found']

    let errorMessage = '';

    if (error.error instanceof ErrorEvent) {
      errorMessage = error.error.message;
    } else if (error_types.includes(error.error.message)) {
      errorMessage = 'left_sidebar.layer.s3_' + error.error.message;
    } else {
      errorMessage = `Error Code: ${error.status}\nMessage: ${error.message}`;
    }

    return of({ status: 'error', message: errorMessage });
  }
}
