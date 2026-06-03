/**
 * Angular imports.
 */
import { Injectable } from '@angular/core';

/**
 * Core imports.
 */
import { WmtsService, RegionFilterService } from '@core/services';
import { DescriptorType } from '@core/interfaces';

/**
 * OpenLayers imports.
 */
import { WMTS, XYZ } from 'ol/source';
import GeoTIFF from 'ol/source/GeoTIFF';
import CanvasTileLayer from 'ol/layer/Tile';
import TileLayer from 'ol/layer/WebGLTile';
import BaseLayer from 'ol/layer/Base';

import { MapService, ZOOM_LIMIT } from './map.service';
import { environment } from 'src/environments/environment';
import { Options, optionsFromCapabilities } from 'ol/source/WMTS';

export { LayerService };

@Injectable({
  providedIn: 'root',
})
class LayerService {
  private urls: string[] = [
    environment.OWS_O1,
    environment.OWS_O2,
    environment.OWS_O3,
    environment.OWS_O4,
  ];

  private bufferWmtsCapabilities: Options[] = [];

  constructor(
    private mapService: MapService,
    private wmtsService: WmtsService,
    private regionFilterService: RegionFilterService
  ) {}

  public createLayer(descriptorType: DescriptorType): Promise<BaseLayer> | null {
    switch (descriptorType.origin.typeOfTMS) {
      case 'wmts':
        return this.createTileLayerWMTS(descriptorType);
      case 'xyz':
        return this.createTileLayerXYZ(descriptorType);
      case 'cog':
        return this.createWebGLTileLayerCOG(descriptorType);
      default:
        throw new Error(`Unsupported TMS type: ${descriptorType.origin.typeOfTMS}`);
    }
  }

  private getLayerZIndex(type: string): number {
    if (type === 'basemap') return 0;
    if (type === 'limit') return 1000;
    return 10;
  }

  private createWebGLTileLayerCOG(descriptorType: DescriptorType): Promise<TileLayer> {
    const properties = {
      key: descriptorType.valueType,
      label: descriptorType.viewValueType,
      descriptorType: descriptorType,
      type: descriptorType.type,
      visible: descriptorType.visible,
    };

    const source = new GeoTIFF({
      normalize: false,
      interpolate: false,
      loadMissingProjection: true,
      projection: descriptorType.projection || descriptorType.origin.epsg || 'EPSG:3857',
      wrapX: true,
      transition: 0,
      sources: [
        {
          url: descriptorType.origin.url!,
        },
      ],
    });

    const layer = new TileLayer({
      properties: properties,
      source: source,
      style: descriptorType.cogStyle,
      visible: descriptorType.visible,
      opacity: descriptorType.opacity,
      zIndex: this.getLayerZIndex(descriptorType.type)
    });

    return new Promise<TileLayer>((resolve) => {
      resolve(layer);
    });
  }

  // TODO: Implement this method.
  private createTileLayerXYZ(descriptorType: DescriptorType): Promise<CanvasTileLayer<XYZ>> {
    let properties = {
      key: descriptorType.valueType,
      label: descriptorType.viewValueType,
      descriptorType: descriptorType,
      type: descriptorType.type,
      visible: descriptorType.visible,
    };

    return new Promise<CanvasTileLayer<XYZ>>((resolve) => {
      resolve(
        new CanvasTileLayer<XYZ>({
          properties: properties,
          source: new XYZ({ urls: this.parseURLs(descriptorType) }),
          visible: descriptorType.visible,
          zIndex: this.getLayerZIndex(descriptorType.type)
        })
      );
    });
  }

  // TODO: Implement this method.
  private createTileLayerWMTS(
    descriptorType: DescriptorType
  ): Promise<CanvasTileLayer<WMTS>> {
    const properties = {
      key: descriptorType!.valueType,
      label: descriptorType!.viewValueType,
      descriptorType: descriptorType,
      type: descriptorType.type,
      visible: descriptorType.visible,
    };

    return new Promise<CanvasTileLayer<WMTS>>((resolve, reject) => {
      this.wmtsService.getCapabilities(descriptorType.origin.url).subscribe({
        next: (capabilities: any) => {
          const options: Options = optionsFromCapabilities(capabilities, {
            layer: descriptorType.filterSelected,
            matrixSet: descriptorType.origin.epsg,
          })!;

          this.bufferWmtsCapabilities[descriptorType.valueType] = options;

          resolve(
            new CanvasTileLayer({
              properties: properties,
              source: new WMTS(options),
              visible: descriptorType.visible,
              zIndex: this.getLayerZIndex(descriptorType.type)
            })
          );
        },
        error: (error: Error) => {
          reject(error);
        },
      });
    });
  }

  //TODO: Reduzir para false.
  public parseURLs(descriptorType: DescriptorType, highResolution: boolean = true): string[]  {
    switch (descriptorType.type) {
      case 'limit':
        return this.parseLimitURL(descriptorType)
      case 'layertype':
        return this.parseLayersURL(descriptorType, highResolution)
      default:
        throw new Error('Invalid source service.');
    }
  }

  public parseLimitURL(descriptorType): string[] {
    let layerName = descriptorType.valueType;

    let parsedLimitUrl = this.urls.map((url: string) => {
      return `${url}?layers=${layerName}&MSFILTER=&mode=tile&tile={x}+{y}+{z}&tilemode=gmap&map.imagetype=png`;
    })

    console.log(parsedLimitUrl)

    return parsedLimitUrl;
  }

  public parseLayersURL(descriptorType: DescriptorType, highResolution: boolean): string[] {
    switch (descriptorType.origin.sourceService) {
      case 'external':
        return this.parseExternalURLs(descriptorType);
      case 'internal':
        return this.parseInternalURLs(descriptorType, highResolution);
      default:
        throw new Error('Invalid source service.');
    }
  }

  private parseExternalURLs(descriptorType: DescriptorType): string[] {
    const filter: string = descriptorType.filterSelected!;

    let layer = descriptorType.origin.url!.replace('{{filters.valueFilter}}', filter);

    return [layer]
  }

  private parseInternalURLs(descriptorType: DescriptorType, highResolution: boolean): string[] {
    let filters: string[] = [];

    let layername = highResolution ? descriptorType.download?.layerTypeName : descriptorType.valueType;
    
    filters = filters.concat(this.parseMsFilter(descriptorType))

    if (descriptorType.filterHandler == 'layername') {
      if (descriptorType.filterSelected != null) {
        layername = descriptorType!.filterSelected;
      }
    }

    return this.urls.map((url: string) => {
      return `${url}?layers=${layername}&MSFILTER=${filters.join(' AND ')}&mode=tile&tile={x}+{y}+{z}&tilemode=gmap&map.imagetype=png`;
    });
  }

  private parseMsFilter(descriptorType: DescriptorType): string[] {
    let filters: string[] = [];

    const usesMsFilter = descriptorType.filterHandler === 'msfilter' || descriptorType.regionFilter === true;

    if (descriptorType.filterHandler === 'msfilter' && descriptorType.filterSelected) {
      filters.push(descriptorType.filterSelected);
    }

    if (descriptorType.regionFilter && this.regionFilterService.hasMsFilter) {
      filters.push(this.regionFilterService.currentMsFilter);
    }

    if (filters.length === 0 && usesMsFilter) {
      filters.push('true');
    }

    return filters;
  }
};
