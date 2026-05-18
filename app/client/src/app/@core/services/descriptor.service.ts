//TODO: Criar um observable dinamico para cada layer sob demanda;

/**
 * Angular imports.
 */
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

/**
 * Interfaces imports.
 */
import { Descriptor, DescriptorGroup, DirtyType } from '@core/interfaces';
import { DescriptorLayer, DescriptorType } from '@core/interfaces';

/**
 * Rxjs imports.
 */
import { BehaviorSubject, Observable } from 'rxjs';
import { LocalizationService } from '@core/internationalization/localization.service';
import { LangChangeEvent } from '@ngx-translate/core';

const HTTP_URL = '/service/map';

@Injectable({
  providedIn: 'root',
})
class DescriptorService {
  private descriptor: Descriptor | null = null;

  private descriptor$ = new BehaviorSubject<Descriptor | null>(this.descriptor);

  constructor(
    private httpClient: HttpClient,
    private localizationService: LocalizationService
  ) {
    this.localizationService.translateService.onLangChange.subscribe(
      (langChangeEvent: LangChangeEvent) => {
        this.fetchDescriptor(langChangeEvent.lang)
      }
    );
  }

  public getDescriptor(): Observable<Descriptor | null> {
    if (this.descriptor === null) {
      let lang = this.localizationService.currentLang();

      this.fetchDescriptor(lang);
    }

    return this.descriptor$;
  }

  public getDescriptorValue(): Descriptor | null {
    return this.descriptor;
  }

  private fetchDescriptor(lang: string): void {
    this.httpClient.get<any>(`${HTTP_URL}/descriptor?lang=${lang}`).subscribe({
      next: (descriptor: any) => {
        this.setDescriptor(descriptor);
      },
      error: (error: any) => {
        console.error('Error occourde while loading descriptor.', error);
      },
    });
  }

  private setDescriptor(descriptor: Descriptor): void {
    this.descriptor = descriptor;

    this.descriptor.dirtyBit = { dirty: DirtyType.CLEAN };

    this.setBasemaps();
    this.setGroups();
    this.setLimits();

    this.descriptor$.next(this.descriptor);
  }

  private setBasemaps(): void {
    this.descriptor!.basemaps.forEach((basemap: DescriptorLayer) => {
      basemap.selectedTypeObject = basemap.types.find(
        (type: DescriptorType) => type.valueType === basemap.selectedType
      );

      if (basemap.selectedTypeObject) {
        basemap.selectedTypeObject!.visible = basemap.visible;
      }
    });
  }

  private setGroups(): void {
    this.descriptor!.groups.forEach((group: DescriptorGroup) => {
      group.layers.forEach((layer: DescriptorLayer) => {
        layer.opacity = 100;

        layer.selectedTypeObject = layer.types.find(
          (type: DescriptorType) => type.valueType === layer.selectedType
        );

        if (layer.selectedTypeObject) {
          layer.selectedTypeObject!.visible = layer.visible;
        }
      });
    });
  }

  private setLimits(): void {
    this.descriptor!.limits.forEach((limit: DescriptorLayer) => {
      limit.selectedTypeObject = limit.types.find(
        (type: DescriptorType) => type.valueType === limit.selectedType
      );

      if (limit.selectedTypeObject) {
        limit.selectedTypeObject!.visible = limit.visible;
      }
    });
  }

  private setDirtyBit(type: DirtyType, layer: string, layerType: string): void {
    if (this.descriptor == null) return;

    this.descriptor.dirtyBit = {
      dirty: type,
      layer: layer,
      layerType: layerType,
    };
  }

  public updateBasemapVisibility(key: string, visible: boolean): void {
    if (this.descriptor === null) return;

    let targetLayerId = key;

    this.descriptor.basemaps.forEach((basemap: DescriptorLayer) => {
      let isTargetLayer = basemap.idLayer === key;
      let targetType = basemap.types.find(
        (t: DescriptorType) => t.valueType === key
      );

      if (isTargetLayer || targetType) {
        targetLayerId = basemap.idLayer;
        if (targetType) {
          basemap.selectedType = key;
          basemap.selectedTypeObject = targetType;
        }

        basemap.visible = visible;

        basemap.types.forEach((t: DescriptorType) => {
          if (t.valueType === basemap.selectedType) {
            t.visible = visible;
          } else {
            t.visible = false;
          }
        });
      } else if (visible) {
        basemap.visible = false;
        basemap.types.forEach((t: DescriptorType) => {
          t.visible = false;
        });
      }
    });

    this.setDirtyBit(DirtyType.VISIBILITY, targetLayerId, 'basemap');
    this.descriptor$.next(this.descriptor);
  }

  public updateLayerVisibility(idLayer: string, visible: boolean): void {
    if (this.descriptor === null) return;

    this.setDirtyBit(DirtyType.VISIBILITY, idLayer, 'layertype');

    this.descriptor.groups.forEach((group: DescriptorGroup) => {
      group.layers.forEach((layer: DescriptorLayer) => {
        if (layer.idLayer !== idLayer) return;

        layer.visible = visible;
      });
    });

    this.descriptor$.next(this.descriptor);
  }

  public updateLayerTransparency(idLayer: string, value: number): void {
    if (this.descriptor === null) return;

    this.setDirtyBit(DirtyType.TRANSPARENCY, idLayer, 'layertype');

    this.descriptor!.groups.forEach((group: DescriptorGroup) => {
      group.layers.forEach((layer: DescriptorLayer) => {
        if (layer.idLayer !== idLayer) return;

        layer.opacity = value / 100;
      });
    });

    this.descriptor$.next(this.descriptor);
  }

  public updateLayerType(idLayer: string, valueType: string): void {
    if (this.descriptor === null) return;

    this.setDirtyBit(DirtyType.TYPE, idLayer, 'layertype');

    this.descriptor.groups.forEach((group: DescriptorGroup) => {
      group.layers.forEach((layer: DescriptorLayer) => {
        if (layer.idLayer !== idLayer) return;

        layer.types.forEach((type: DescriptorType) => {
          if (type.valueType === valueType) {
            layer.selectedType = valueType;
            layer.selectedTypeObject = type;
          }
        });
      });
    });

    this.descriptor$.next(this.descriptor);
  }

  public updateLayerFilter(idLayer: string, filter: string): void {
    if (this.descriptor === null) return;

    this.setDirtyBit(DirtyType.SOURCE, idLayer, 'layertype');

    this.descriptor.groups.forEach((group: DescriptorGroup) => {
      group.layers.forEach((layer: DescriptorLayer) => {
        if (layer.idLayer !== idLayer) return;

        layer.selectedTypeObject!.filterSelected = filter;
      });
    });

    this.descriptor$.next(this.descriptor);
  }

  public updateLimitVisibility(key: string, visible: boolean): void {
    if (this.descriptor === null) return;

    let targetLayerId = key;

    this.descriptor.limits.forEach((limit: DescriptorLayer) => {
      let isTargetLayer = limit.idLayer === key;
      let targetType = limit.types.find(
        (t: DescriptorType) => t.valueType === key
      );

      if (isTargetLayer || targetType) {
        targetLayerId = limit.idLayer;
        if (targetType) {
          limit.selectedType = key;
          limit.selectedTypeObject = targetType;
        }

        limit.visible = visible;

        limit.types.forEach((t: DescriptorType) => {
          if (t.valueType === limit.selectedType) {
            t.visible = visible;
          } else {
            t.visible = false;
          }
        });
      } else if (visible) {
        limit.visible = false;
        limit.types.forEach((t: DescriptorType) => {
          t.visible = false;
        });
      }
    });

    this.setDirtyBit(DirtyType.VISIBILITY, targetLayerId, 'limits');
    this.descriptor$.next(this.descriptor);
  }

  public changeGroupExpandedState(groupId: string): void {
    if (this.descriptor == null) return;

    let group = this.descriptor.groups.find((group: DescriptorGroup) => {
      return group.idGroup == groupId;
    })!;

    group.groupExpanded = !group.groupExpanded;

    this.descriptor$.next(this.descriptor);
  }

  // TODO: Na verdade ele esta retornando a unica layer que existe e trabalhando com suas propriedades;
  public getBsemapById(basemapId: string): DescriptorLayer {
    return this.descriptor?.basemaps.find(
      (basemap) => basemap.idLayer === basemapId
    )!;
  }

  public getLayer(layerId: string): DescriptorLayer {
    let result: DescriptorLayer;

    this.descriptor?.groups.forEach((descriptorGroup: DescriptorGroup) => {
      descriptorGroup.layers.forEach((descriptorLayer: DescriptorLayer) => {
        if (descriptorLayer.idLayer !== layerId) return;

        result = descriptorLayer;
      });
    });

    return result!;
  }

  public getType(valueType: string): DescriptorType {
    let result: DescriptorType;

    this.descriptor?.groups.forEach((group: DescriptorGroup) => {
      group.layers.forEach((layer: DescriptorLayer) => {
        layer.types.forEach((type: DescriptorType) => {
          if (type.valueType !== valueType) return;

          result = type;
        });
      });
    });

    return result!;
  }

  public getLimit(limitId: string): DescriptorLayer {
    return this.descriptor?.limits.find((limit) => limit.idLayer === limitId)!;
  }

  // TODO: Não deve exister, resolver problemas associados com reconstrução do descriptor;
  public refresh(): void {
    this.descriptor$.next(this.descriptor);
  }
}

export { DescriptorService };
