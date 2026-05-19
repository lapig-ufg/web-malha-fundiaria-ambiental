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
    console.log(`Creating layer for ${descriptorType.valueType} (TMS: ${descriptorType.origin.typeOfTMS})`);
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
      projection: 'ESRI:102033', // Force correct projection for meter-based coordinates
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
      style: {
        color: [
          'case',
          ['==', ['band', 1], 0], [0, 0, 0, 0], // Transparent for value 0
          ['palette', ['band', 1], [
            [0, 0, 0, 0],       // Index 0
            [0, 0, 205],       // 1: Massa d'água
            [108, 116, 126],   // 2: Malha Urbana
            [131, 61, 201],    // 3: TI Homologada
            [100, 239, 239],   // 4: UC Proteção Integral
            [205, 115, 160],   // 5: Área Militar
            [253, 174, 97],    // 6: Imóvel Privado
            [168, 225, 110],   // 7: Assentamento
            [23, 175, 5],      // 8: Glebas Públicas - FPND
            [239, 239, 77],    // 9: UC Uso Sustentável
            [220, 16, 16],     // 10: Glebas Públicas
            [69, 135, 202],    // 11: Quilombola Declarado
            [51, 51, 230],     // 12: TI Não Homologada
            [68, 206, 68],     // 13: Quilombola Não Declarado
            [207, 60, 207],    // 14: CAR sem sobreposição
            [255, 99, 106],    // 15: CAR com sobreposição
            [0, 0, 0, 0],      // 16
            [0, 0, 0, 0],      // 17
            [0, 0, 0, 0],      // 18
            [0, 0, 0, 0],      // 19
            [230, 233, 180],   // 20: Área de Preservação Permanente
            [30, 87, 13]       // 21: Reserva Legal
          ]]
        ]
      },
      visible: descriptorType.visible,
      opacity: descriptorType.opacity
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

    return this.urls.map((url: string) => {
      return `${url}?layers=${layerName}&MSFILTER=&mode=tile&tile={x}+{y}+{z}&tilemode=gmap&map.imagetype=png`;
    });
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

    if (descriptorType.regionFilter) {
      filters.push(descriptorType.regionFilter.toString());
    }

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
    if (descriptorType.filterHandler !== 'msfilter') return []

    let filters: string[] = [];

    filters.push(descriptorType.filterSelected!);

    if (descriptorType.regionFilter) {
      if (this.regionFilterService.hasMsFilter) {
        filters.push(this.regionFilterService.currentMsFilter);
      }
    }

    return filters;
  }
};
