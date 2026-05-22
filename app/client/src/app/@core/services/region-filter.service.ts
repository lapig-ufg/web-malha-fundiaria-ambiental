import { Injectable } from '@angular/core';
import { RegionFilter } from '@core/interfaces';
import { BehaviorSubject, Observable } from 'rxjs';

export const DEFAULT_REGION = {
  type: 'country',
  text: 'Brasil',
  value: 'BRASIL',
};

@Injectable({
  providedIn: 'root',
})
export class RegionFilterService {
  private filterRegion: RegionFilter = DEFAULT_REGION;
  private msFilterRegion: string = ''

  private region$ = new BehaviorSubject<RegionFilter>(this.filterRegion);

  get currentFilter(): RegionFilter {
    return {...this.filterRegion};
  }

  get currentMsFilter(): string {
    return this.msFilterRegion;
  }

  get hasMsFilter(): boolean {
    return this.msFilterRegion !== '';
  }

  public getRegionFilter(): Observable<RegionFilter> {
    return this.region$;
  }

  public updateRegionFilter(newFilter: RegionFilter): void {
    this.filterRegion = newFilter;

    switch (newFilter.type) {
      case 'city':
        this.msFilterRegion = `cd_geocmu = '${newFilter.value}'`;
        break;
      case 'state':
        this.msFilterRegion = `uf ilike '${newFilter.value}'`;
        break;
      default:
        this.msFilterRegion = '';
        break;
    }

    this.region$.next(newFilter);
  }
}
