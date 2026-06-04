/**
 * Angular imports.
 */
import { Injectable } from '@angular/core';

/**
 * Rxjs imports.
 */
import { BehaviorSubject, Observable } from 'rxjs';

/**
 * Selected feature shape published by the map (click) and the filter
 * (CAR search) and consumed by the statistics sidebar to drive the
 * per-property zonal chart.
 */
export interface SelectedFeature {
  /** Source layer id, e.g. 'malha_fundiaria_ambiental'. */
  idLayer: string;
  /** Original feature properties, may be null. */
  properties: { [key: string]: any } | null;
  /** GeoJSON Feature (the entire feature object). */
  geometry: any;
}

@Injectable({
  providedIn: 'root',
})
class SelectedFeatureService {
  private readonly subject = new BehaviorSubject<SelectedFeature | null>(null);

  public getSelectedFeature(): Observable<SelectedFeature | null> {
    return this.subject.asObservable();
  }

  public get current(): SelectedFeature | null {
    return this.subject.value;
  }

  public set(feature: SelectedFeature | null): void {
    this.subject.next(feature);
  }

  public clear(): void {
    this.subject.next(null);
  }
}

export { SelectedFeatureService };
