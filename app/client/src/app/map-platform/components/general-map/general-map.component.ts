// TODO: O botão de resetar zoom ou não deveria resetar a geometri ou não deveria se chamar resetar zoom.

/**
 * Angular imports.
 */
import { OnDestroy } from '@angular/core';
import { ElementRef, HostListener } from '@angular/core';
import { EventEmitter, OnInit, Output, ViewChild, Component } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { CdkDragDrop, moveItemInArray } from '@angular/cdk/drag-drop';

/**
 * PrimeNg imports.
 */
import { MessageService } from 'primeng/api';
import { PrimeNGConfig, SelectItem } from 'primeng/api';

/**
 * OpenLayers imports.
 */
import Map from 'ol/Map';
import BaseLayer from 'ol/layer/Base';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import CircleStyle from 'ol/style/Circle';
import VectorSource from 'ol/source/Vector';
import * as Proj from 'ol/proj';
import { MapEvent, Overlay } from 'ol';
import { Interaction, Modify, Snap } from 'ol/interaction';
import { BingMaps, XYZ } from 'ol/source';
import { GeoJSON } from 'ol/format';
import { Extent } from 'ol/extent';
import { Fill, Stroke, Style } from 'ol/style';
import { transform, transformExtent } from 'ol/proj';
import { Pixel } from 'ol/pixel';
import * as OlExtent from 'ol/extent.js';

/**
 * Core imports.
 */
import { LocalizationService } from '@core/internationalization/localization.service';

/**
 * Interfaces imports.
 */
import { Job, RegionFilter } from '@core/interfaces';
import { DirtyType, LayerLegend } from '@core/interfaces';
import { Descriptor, DescriptorType } from '@core/interfaces';
import { DescriptorGroup, DescriptorLayer } from '@core/interfaces';

/**
 * Services imports.
 */
import {
  DownloadService,
  MapAPIService,
} from '../../../@core/services';
import { RegionFilterService, DEFAULT_REGION } from '../../../@core/services';
import { GoogleAnalyticsService } from '../../../@core/services';
import { DescriptorService } from '../../../@core/services';
import { SelectedFeatureService } from '../../../@core/services';

import { MapService } from '@core/services/map.service';

import { saveAs } from 'file-saver';

/**
 * PDFMaker imports.
 */
//import pdfMake from 'pdfmake/build/pdfmake';
//import pdfFonts from 'pdfmake/build/vfs_fonts';

/**
 * TURF imports.
 */
import * as turfHelper from '@turf/helpers';
import buffer from '@turf/buffer';
import turfDistance from '@turf/distance';
import booleanPointInPolygon from '@turf/boolean-point-in-polygon';
import turfCentroid from '@turf/centroid';

/**
 * Environment imports.
 */
import { environment } from '../../../../environments/environment';

/**
 * RXJS imports.
 */
import { Subscription } from 'rxjs';

/**
 * NgRecaptcha imports.
 */
import { OlMapComponent } from '@core/components/ol-map/ol-map.component';
import { LayerService } from '@core/services/layer.service';
import { UserInfoComponent } from '@core/components/user-info-dialog/user-info-dialog.component';

//pdfMake.vfs = pdfFonts.pdfMake.vfs;

// TODO: Medição não parece estar funcionando legal. Não é possivel cancelar o clique e manter a figura no mapa.
// TODO: Quando desenha poligonos ao terminar o desenho:
//    a) As vezes não é possivel fechar o poligono pois o texto fica na frente.
//    b) Ele abre as informações do ponto que foi clicado por ultimo.

const PROJECTION = Proj.get('EPSG:900913');

const PRIMARY_COLOR = window
  .getComputedStyle(document.body)
  .getPropertyValue('--primary')
  .trim();


/**
 * Componente responsável por gerenciar e manipular o WebMap por meio do framework OpenLayers.
 * 
 * @component
 */
@Component({
  standalone: false,
  selector: 'app-general-map',
  templateUrl: './general-map.component.html',
  styleUrls: [
    './general-map.component.scss',
    './responsivity/general-map.component-mobile.scss',
  ],
  providers: [MessageService],
})
export class GeneralMapComponent implements OnInit, OnDestroy {
  @ViewChild(UserInfoComponent) userInfo!: UserInfoComponent;

  @ViewChild('video') video!: ElementRef;
  @ViewChild('wfsCard') wfsCard!: ElementRef;

  @ViewChild(OlMapComponent) olMap!: OlMapComponent;

  /**
   * Emitted when a malha_fundiaria feature is selected on the map (level-2
   * click) so the parent (MainComponent) can auto-open the right-hand
   * statistics sidebar.
   */
  @Output() openStatisticsSidebar = new EventEmitter<void>();

  public features: any[] = [];

  public mapSubscription: Subscription = new Subscription();
  public descriptorSubscription: Subscription = new Subscription();
  public regionFilterSubscription: Subscription = new Subscription();

  public env: any = environment;

  public action!: Function;

  public bmaps: any = [
    {
      layer: new TileLayer({
        properties: {
          key: 'mapbox',
          type: 'bmap',
          visible: true,
        },
        source: new XYZ({
          wrapX: false,
          url: 'https://api.mapbox.com/styles/v1/mapbox/light-v10/tiles/{z}/{x}/{y}?access_token=pk.eyJ1IjoidGhhcmxlc2FuZHJhZGUiLCJhIjoiY2thaHAxcDM5MGx2dzJ4dDExaGQ0bGF3ciJ9.kiB2OzG3Q0THur8XLUW3Gg',
        }),
        visible: true,
      }),
    },
    {
      layer: new TileLayer({
        properties: {
          key: 'mapbox-dark',
          type: 'bmap',
          visible: false,
        },
        source: new XYZ({
          wrapX: false,
          url: 'https://api.mapbox.com/styles/v1/mapbox/dark-v10/tiles/{z}/{x}/{y}?access_token=pk.eyJ1IjoidGhhcmxlc2FuZHJhZGUiLCJhIjoiY2thaHAxcDM5MGx2dzJ4dDExaGQ0bGF3ciJ9.kiB2OzG3Q0THur8XLUW3Gg',
        }),
        visible: false,
      }),
    },
    {
      layer: new TileLayer({
        properties: {
          key: 'bing',
          type: 'bmap',
          visible: false,
        },
        preload: Infinity,
        source: new BingMaps({
          key: 'VmCqTus7G3OxlDECYJ7O~G3Wj1uu3KG6y-zycuPHKrg~AhbMxjZ7yyYZ78AjwOVIV-5dcP5ou20yZSEVeXxqR2fTED91m_g4zpCobegW4NPY',
          imagerySet: 'Aerial',
        }),
        visible: false,
      }),
    },
    {
      layer: new TileLayer({
        properties: {
          key: 'google',
          type: 'bmap',
          visible: false,
        },
        source: new XYZ({
          url: 'https://mt{0-3}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
        }),
        visible: false,
      }),
    },
    {
      layer: new TileLayer({
        properties: {
          key: 'google-hybrid',
          type: 'bmap',
          visible: false,
        },
        source: new XYZ({
          url: 'https://mt{0-3}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        }),
        visible: false,
      }),
    },
    {
      layer: new TileLayer({
        properties: {
          key: 'estradas',
          type: 'bmap',
          visible: false,
        },
        preload: Infinity,
        source: new BingMaps({
          key: 'VmCqTus7G3OxlDECYJ7O~G3Wj1uu3KG6y-zycuPHKrg~AhbMxjZ7yyYZ78AjwOVIV-5dcP5ou20yZSEVeXxqR2fTED91m_g4zpCobegW4NPY',
          imagerySet: 'Road',
        }),
        visible: false,
      }),
    },
    {
      layer: new TileLayer({
        properties: {
          key: 'relevo',
          type: 'bmap',
          visible: false,
        },
        source: new XYZ({
          url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}',
        }),
        visible: false,
      }),
    },
    {
      layer: new TileLayer({
        properties: {
          key: 'planet',
          type: 'bmap',
          visible: false,
        },
        source: new XYZ({
          url: 'https://tiles{0-3}.planet.com/basemaps/v1/planet-tiles/global_quarterly_2021q2_mosaic/gmap/{z}/{x}/{y}.png?api_key=d6f957677fbf40579a90fb3a9c74be1a',
        }),
        visible: false,
      }),
    },
  ];

  public layersLegend: LayerLegend[] = [];
  public selectedLayers: string[] = [];

  private isLayerHighResolution: boolean = false;

  public showFormPoint: boolean = false;
  public _displayLayers!: boolean;
  public showRightSideBar!: boolean;
  public drawing: boolean = false;
  public lat!: number;
  public lon!: number;
  public classes!: string;

  public popupOverlay!: Overlay;

  public featureCollections: any[] = [];

  public popupRegion: any = {
    coordinate: [],
    attributes: [],
    properties: {},
    geojson: {},
  };

  public year: any;
  public isShowIformats: boolean = true;

  public geoJsonStyles: any = {
    Point: new Style({
      image: new CircleStyle({
        radius: 5,
        stroke: new Stroke({
          color: PRIMARY_COLOR,
          width: 1,
        }),
      }),
    }),
    LineString: new Style({
      stroke: new Stroke({
        color: PRIMARY_COLOR,
        width: 1,
      }),
    }),
    MultiLineString: new Style({
      stroke: new Stroke({
        color: PRIMARY_COLOR,
        width: 1,
      }),
    }),
    MultiPoint: new Style({
      image: new CircleStyle({
        radius: 5,
        stroke: new Stroke({ color: 'red', width: 1 }),
      }),
    }),
    MultiPolygon: new Style({
      stroke: new Stroke({
        color: PRIMARY_COLOR,
        width: 1,
      }),
      fill: new Fill({
        color: 'rgba(255, 255, 0, 0.1)',
      }),
    }),
    Polygon: new Style({
      stroke: new Stroke({
        color: PRIMARY_COLOR,
        lineDash: [5],
        width: 3,
      }),
      fill: new Fill({
        color: 'rgba(22, 38, 35, 0.4)',
      }),
    }),
    GeometryCollection: new Style({
      stroke: new Stroke({
        color: PRIMARY_COLOR,
        width: 2,
      }),
      fill: new Fill({
        color: 'magenta',
      }),
      image: new CircleStyle({
        radius: 10,
        stroke: new Stroke({
          color: PRIMARY_COLOR,
        }),
      }),
    }),
    Circle: new Style({
      stroke: new Stroke({
        color: PRIMARY_COLOR,
        width: 2,
      }),
      fill: new Fill({
        color: 'rgba(255,0,0,0.2)',
      }),
    }),
  };

  public displayFilters: boolean = false;

  public otherLayerFromFilters: any = {
    layer: null,
    strokeColor: '#363230',
  };

  public legendExpanded: boolean = true;
  public searchBarVisible: boolean = true;
  public isMobile: boolean;

  public drillDownLevel: number = 0;

  public malhaSearchValue: any = { text: '' };
  public malhaSearchSuggestions: any[] = [];
  public malhaSearchLoading: boolean = false;
  public searchCategory: string = 'malha';
  public searchCategoryOptions: any[] = [
    { label: 'controls.search_categories.malha', value: 'malha', icon: 'home' },
    { label: 'controls.search_categories.estado', value: 'estado', icon: 'map' },
    { label: 'controls.search_categories.municipio', value: 'municipio', icon: 'location_city' },
    { label: 'controls.search_categories.bioma', value: 'bioma', icon: 'nature_people' },
  ];
  private malhaVectorLayer: any;

  public displayFormJob: boolean = false;
  public job!: Job;
  public emailValid: boolean = true;

  constructor(
    private layerService: LayerService,
    private mapService: MapService,
    private descriptorService: DescriptorService,
    private regionFilterService: RegionFilterService,
    public localizationService: LocalizationService,
    private downloadService: DownloadService,
    private decimalPipe: DecimalPipe,
    private mapAPIService: MapAPIService,
    private messageService: MessageService,
    private primengConfig: PrimeNGConfig,
    private googleAnalyticsService: GoogleAnalyticsService,
    private selectedFeatureService: SelectedFeatureService,
  ) {
    this.action = this.initDescriptor;

    this.descriptorSubscription.add(
      descriptorService.getDescriptor().subscribe({
        next: (descriptor: Descriptor | null) => {
          if (descriptor == null) return;

          console.log('Map Descriptor:', descriptor);
          this.action(descriptor);
        },
      })
    );

    this.regionFilterSubscription.add(
      regionFilterService.getRegionFilter().subscribe({
        next: (filter: RegionFilter) => {
          this.refreshLayersSource()
        },
      })
    )

    if (
      /Android|webOS|iPhone|iPad|iPod|BlackBerry|BB|PlayBook|IEMobile|Windows Phone|Kindle|Silk|Opera Mini/i.test(
        navigator.userAgent
      )
    ) {
      this.legendExpanded = false;
      this.isMobile = true;
    } else {
      this.isMobile = false;
    }

    this.mapService.addEvent('moveend', (event: MapEvent) =>

      this.onZoom(event)
    );

    this.mapService.addEvent('singleclick', (event: MapEvent) =>
      this.onDisplayFeatureInfo(event)
    );
  }

  public ngOnInit(): void {
    const self = this;
    this.primengConfig.ripple = true;
  }

  public ngOnDestroy(): void {
    this.descriptorSubscription.unsubscribe();
    this.mapSubscription.unsubscribe();
  }

  private onZoom(event: MapEvent): void {
    let zoom = event.map.get('view').get('zoom');

    if (!this.isLayerHighResolution && zoom >= 9) {
      this.isLayerHighResolution = true;

      this.refreshLayersSource();
    } else if (this.isLayerHighResolution && zoom < 9) {
      this.isLayerHighResolution = false;

      this.refreshLayersSource();
    }

    this.refreshLayersVisibilityByZoom(zoom);
  }

  public resetDrillDown() {
    this.drillDownLevel = 0;
    this.mapService.resetZoom();
    this.refreshDrillDownLimits();
    this.closePopup();

    // Reset region filter when user resets drill-down navigation
    this.regionFilterService.updateRegionFilter(DEFAULT_REGION);
  }

  private refreshDrillDownLimits(): void {
    const descriptor = this.descriptorService.getDescriptorValue();
    if (!descriptor) return;

    descriptor.limits.forEach((limit) => {
      let visible = false;
      if (this.drillDownLevel === 0 && limit.idLayer === 'estados')
        visible = true;
      if (this.drillDownLevel === 1 && limit.idLayer === 'municipios')
        visible = true;
      if (
        this.drillDownLevel === 2 &&
        limit.idLayer === 'malha_fundiaria_ambiental'
      )
        visible = true;

      if (limit.selectedTypeObject) {
        limit.selectedTypeObject.visible = visible;
      }

      this.updateLimitVisibility(
        limit,
        this.mapService.map.getView().getZoom() || 0
      );
    });
  }

  private refreshLayersVisibilityByZoom(zoom: number): void {
    const descriptor = this.descriptorService.getDescriptorValue();
    if (!descriptor) return;

    descriptor.basemaps.forEach((basemap) =>
      this.updateBasemapVisibility(basemap, zoom)
    );
    descriptor.groups.forEach((group) =>
      group.layers.forEach((layer) => this.updateLayerVisibility(layer, zoom))
    );
    descriptor.limits.forEach((limit) =>
      this.updateLimitVisibility(limit, zoom)
    );
  }

  private initDescriptor(descriptor: Descriptor) {
    this.refreshDrillDownLimits();
    this.initBasemaps(descriptor.basemaps);
    this.initLayers(descriptor.groups);
    this.initLimits(descriptor.limits);

    this.initLayersSelected(descriptor.groups);

    this.action = this.updateDescriptor;

    this.refreshLayersVisibilityByZoom(
      this.mapService.map.getView().getZoom() || 0
    );
  }

  private initBasemaps(basemaps: DescriptorLayer[]): void {
    basemaps.forEach((basemap: DescriptorLayer) => {
      basemap.types.forEach((type: DescriptorType) => {
        this.bmaps.forEach((bmap: any) => {
          if (type.valueType === bmap.layer.get('key')) {
            bmap.layer.set('descriptorType', type);
            this.mapService.addLayer(bmap.layer);
          }
        });
      });
    });
  }

  private initLayers(groups: DescriptorGroup[]): void {
    groups.forEach((group: DescriptorGroup) => {
      group.layers.forEach((layer: DescriptorLayer) => {
        layer.types.forEach((type: DescriptorType) => {
          this.layerService
            .createLayer(type)
            ?.then((tileLayer: BaseLayer) => {
              this.mapService.addLayer(tileLayer);
              this.updateLayerVisibility(
                layer,
                this.mapService.map.getView().getZoom() || 0
              );
            });
        });
      });
    });
  }

  private initLimits(limits: DescriptorLayer[]): void {
    limits.forEach((limit: DescriptorLayer) => {
      limit.types.forEach((type: DescriptorType) => {
        this.layerService
          .createLayer(type)
          ?.then((tileLayer: BaseLayer) => {
            this.mapService.addLayer(tileLayer);
            this.updateLimitVisibility(
              limit,
              this.mapService.map.getView().getZoom() || 0
            );
          });
      });
    });
  }

  private updateDescriptor(descriptor: Descriptor): void {
    let { dirty, layer, layerType } = descriptor.dirtyBit;

    if (dirty == DirtyType.CLEAN) {
      // If the descriptor is clean but updated, it's likely a language change.
      // Re-initialize the layersLegend to reflect localized labels.
      this.layersLegend = [];
      this.selectedLayers = [];
      this.initLayersSelected(descriptor.groups);
      return;
    }

    switch (layerType) {
      case 'layertype':
        this.handleLayerUpdate(layer!, dirty);
        break;
      case 'basemap':
        this.handleBasemapUpdate(layer!, dirty);
        break;
      case 'limits':
        this.handleLimitUpdate(layer!, dirty);
        break;
    }
  }

  private handleLayerUpdate(layerId: string, dirty: DirtyType): void {
    let descriptorLayer: DescriptorLayer =
      this.descriptorService.getLayer(layerId);

    switch (dirty) {
      case DirtyType.VISIBILITY:
        this.updateLayerVisibility(
          descriptorLayer,
          this.mapService.map.getView().getZoom() || 0
        );

        this.handleLayerSelected(descriptorLayer.selectedTypeObject!);
        break;
      case DirtyType.TRANSPARENCY:
        this.mapService.updateLayerOpacity(
          descriptorLayer.selectedType,
          descriptorLayer.opacity!
        );
        break;
      case DirtyType.SOURCE:
        descriptorLayer.types.forEach((descriptorType: DescriptorType) => {
          this.mapService.updateLayerSource(
            descriptorType.valueType,
            this.layerService.parseURLs(descriptorType)
          );
        });
        break;
      case DirtyType.TYPE:
        descriptorLayer.types.forEach((type: DescriptorType) => {
          this.mapService.updateLayerVisibility(type.valueType, false);
        });

        this.updateLayerVisibility(
          descriptorLayer,
          this.mapService.map.getView().getZoom() || 0
        );

        break;
    }
  }

  public updateLayerVisibility(
    descriptorLayer: DescriptorLayer,
    zoom: number
  ): void {
    let visible = descriptorLayer.visible;

    if (
      descriptorLayer.minZoom !== undefined &&
      zoom < descriptorLayer.minZoom
    ) {
      visible = false;
    }

    this.mapService.updateLayerVisibility(
      descriptorLayer.selectedType,
      visible
    );
  }

  // TODO: Deveria ter uma propriedade no descriptor com a resolução da layer.
  private refreshLayersSource(): void {
    this.mapService.layers.forEach((layer: BaseLayer) => {
      if (layer.get('type') === 'layertype')
        this.mapService.updateLayerSource(
          layer.get('key'),
          this.layerService.parseURLs(
            layer.get('descriptorType'),
            this.isLayerHighResolution
          )
        );
    });
  }

  private handleBasemapUpdate(layerId: string, dirty: DirtyType): void {
    switch (dirty) {
      case DirtyType.VISIBILITY:
        this.refreshLayersVisibilityByZoom(
          this.mapService.map.getView().getZoom() || 0
        );
        break;
    }
  }

  public updateBasemapVisibility(
    descriptorLayer: DescriptorLayer,
    zoom: number
  ): void {
    if (!descriptorLayer.selectedTypeObject) return;

    let visible = descriptorLayer.selectedTypeObject.visible;

    if (
      descriptorLayer.minZoom !== undefined &&
      zoom < descriptorLayer.minZoom
    ) {
      visible = false;
    }

    if (visible) {
      descriptorLayer.types.forEach((descriptorType: DescriptorType) => {
        this.mapService.updateLayerVisibility(descriptorType.valueType, false);
      });
    }

    this.mapService.updateLayerVisibility(
      descriptorLayer.selectedType,
      visible!
    );
  }

  private handleLimitUpdate(layerId: string, dirty: DirtyType): void {
    switch (dirty) {
      case DirtyType.VISIBILITY:
        this.refreshLayersVisibilityByZoom(
          this.mapService.map.getView().getZoom() || 0
        );
        break;
    }
  }

  public updateLimitVisibility(
    descriptorLayer: DescriptorLayer,
    zoom: number
  ): void {
    if (!descriptorLayer.selectedTypeObject) return;

    let visible = descriptorLayer.selectedTypeObject.visible;

    if (
      descriptorLayer.minZoom !== undefined &&
      zoom < descriptorLayer.minZoom
    ) {
      visible = false;
    }

    if (visible) {
      descriptorLayer.types.forEach((descriptorType: DescriptorType) => {
        this.mapService.updateLayerVisibility(descriptorType.valueType, false);
      });
    }

    this.mapService.updateLayerVisibility(
      descriptorLayer.selectedType,
      visible!
    );
  }

  @HostListener('window:resize', ['$event'])
  onResize(event: any) {
    if (
      /Android|webOS|iPhone|iPad|iPod|BlackBerry|BB|PlayBook|IEMobile|Windows Phone|Kindle|Silk|Opera Mini/i.test(
        navigator.userAgent
      )
    ) {
      this.legendExpanded = false;
      this.isMobile = true;
    } else {
      this.isMobile = false;
    }
  }

  searchPoint() {
    if (this.lat && this.lon) {
      this.showFormPoint = !this.showFormPoint;
    }
  }

  private getResolutions(projection: any) {
    let projExtent = projection.getExtent();
    let startResolution = OlExtent.getWidth(projExtent) / 256;
    let resolutions = new Array(22);
    for (let i = 0, ii = resolutions.length; i < ii; ++i) {
      resolutions[i] = startResolution / Math.pow(2, i);
    }
    return resolutions;
  }

  public initLayersSelected(descriptorGroups: DescriptorGroup[]): void {
    descriptorGroups.forEach((descriptorGroup: DescriptorGroup) => {
      descriptorGroup.layers.forEach((descriptorLayer: DescriptorLayer) => {
        descriptorLayer.types.forEach((descriptorType: DescriptorType) => {
          if (!descriptorType.visible) return;
          
          this.selectedLayers.push(descriptorType.valueType);

          this.layersLegend.push({
            key: descriptorType.valueType,
            label: descriptorType.viewValueType,
            filter: descriptorType.filterSelected!,
            filterHandler: descriptorType.filterHandler!,
            expanded: true,
            legend: descriptorType.legend || descriptorLayer.legend
          });
        });
      });
    });

    this.updateZIndex();
  }

  public handleLayerSelected(descriptorType: DescriptorType): void {
    let isIncluded = this.selectedLayers.includes(descriptorType.valueType);

    if (isIncluded) {
      this.selectedLayers = this.selectedLayers.filter(
        (valueType: string) => descriptorType.valueType != valueType
      );

      this.layersLegend = this.layersLegend.filter(
        (layerLegend: LayerLegend) =>
          descriptorType.valueType != layerLegend.key
      );
    } else {
      this.selectedLayers.push(descriptorType.valueType);

      this.layersLegend.push({
        key: descriptorType.valueType,
        label: descriptorType.typeLabel!,
        filter: descriptorType.filterSelected!,
        filterHandler: descriptorType.filterHandler!,
        expanded: true,
        legend: descriptorType.legend
      });
    }

    this.updateZIndex();
  }

  public toggleLayerLegend(legend: LayerLegend): void {
    legend.expanded = !legend.expanded;
  }

  private updateZIndex() {
    this.selectedLayers.forEach((valueType: string, index: number) => {
      this.mapService.updateLayerZIndex(valueType, index + 10);
    });
  }

  public updateLayersOrder(event: CdkDragDrop<string[]>) {
    moveItemInArray(
      this.selectedLayers,
      event.previousIndex,
      event.currentIndex
    );

    moveItemInArray(this.layersLegend, event.previousIndex, event.currentIndex);

    this.updateZIndex();
  }

  downloadSLD(valueType: string) {
    const layerType = this.descriptorService.getType(valueType);

    let name: string | undefined = '';

    if (layerType.filterHandler === 'layername') {
      name = layerType.filterSelected;
    } else {
      name = layerType.valueType;
    }

    this.downloadService
      .downloadRequestSLD(name)
      .toPromise()
      .then((blob: any) => {
        saveAs(blob, name + '.sld');
        layerType.download.loading = false;
      })
      .catch((error) => {
        this.messageService.add({
          life: 2000,
          severity: 'error',
          summary: this.localizationService.translate('sld.msg_error_title'),
          detail: this.localizationService.translate('sld.msg_error', {
            name: name + '.zip',
          }),
        });
      });
  }

  getOverlay(overlay: Overlay) {

    return overlay;
  }

  addOverlay(overlay: Overlay): void {
    let map = this.mapService.map;

    map.addOverlay(overlay);
  }

  onExtentBrazil() {
    let map = this.mapService.map;

    map.getView().fit([], { duration: 900 });
  }

  printRegionsIdentification(token: any) {
    let dd = {
      pageSize: { width: 400, height: 400 },
      pageOrientation: 'portrait',
      content: [],
      styles: {
        titleReport: {
          fontSize: 16,
          bold: true,
        },
        textFooter: {
          fontSize: 9,
        },
        textImglegend: {
          fontSize: 9,
        },
        header: {
          fontSize: 18,
          bold: true,
          margin: [0, 0, 0, 10],
        },
        data: {
          bold: true,
        },
        subheader: {
          fontSize: 16,
          bold: true,
          margin: [0, 10, 0, 5],
        },
        codCar: {
          fontSize: 11,
          bold: true,
        },
        textObs: {
          fontSize: 11,
        },
        tableDpat: {
          margin: [0, 5, 0, 15],
          fontSize: 11,
        },
        tableHeader: {
          bold: true,
          fontSize: 13,
          color: 'black',
        },
        token: {
          bold: true,
          fontSize: 16,
        },
        metadata: {
          background: '#0b4e26',
          color: '#fff',
        },
      },
    };

    // @ts-ignore
    dd.content.push({
      image: this.localizationService.translate('area.token.logo'),
      width: 90,
      alignment: 'center',
    });
    // @ts-ignore
    dd.content.push({
      text: this.localizationService.translate('area.token.description'),
      alignment: 'center',
      margin: [10, 10, 20, 0],
    });
    // @ts-ignore
    dd.content.push({
      text: token,
      alignment: 'center',
      style: 'token',
      margin: [20, 20, 20, 10],
    });

    // @ts-ignore
    dd.content.push({
      qr: 'https://malhafundiaria.lapig.iesa.ufg.br/map/' + token.toString(),
      fit: '200',
      alignment: 'center',
    });

    const filename =
      this.localizationService.translate('area.token.title') +
      ' - ' +
      token +
      '.pdf';
    // const win = window.open('', '_blank');
    // pdfMake.createPdf(dd).open({}, win);
    // TODO: Fix it.
    //pdfMake.createPdf(dd).download(filename);

    this.googleAnalyticsService.eventEmitter(
      'Print_Identification_Token_Layer',
      'Upload',
      'uploadLayer'
    );
  }

  //-----------------> Filters:

  handleFilters(layerType: DescriptorType): string {
    let msFilter = 'true';

    let filters: any[] = [];

    if (layerType.filters!.length > 0) {
      if (layerType!.filterHandler == 'msfilter' && layerType!.filters)
        filters.push(layerType!.filterSelected);

      if (layerType!.regionFilter && this.regionFilterService.currentMsFilter)
        filters.push(this.regionFilterService.currentMsFilter);

      msFilter = filters.join('%20AND%20');
    }

    return '&MSFILTER=' + msFilter;
  }

  //----------------> Features:
  getFeatures(layer: any, bbox: any): Promise<any> {
    return new Promise<any>((resolve) => {
      let typeName = '';
      let msFilter = '&MSFILTER=1=1';
      if (typeof layer === 'string') {
        typeName = layer;
      } else {
        let layerType: DescriptorType = layer.get('descriptorType');
        typeName = layerType.valueType;
        if (layerType.hasOwnProperty('filters')) {
          msFilter = this.handleFilters(layerType);
        }
      }
      const url =
        `${environment.OWS}/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=${typeName}&outputFormat=application/json&bbox=${bbox},EPSG:4326${msFilter}`.trim();
      this.mapAPIService.getFeatures(url).subscribe(
        (features) => {
          features['typeName'] = typeName;
          if (typeof layer === 'string') {
            //do nothing
          } else {
            features['layerType'] = layer.get('descriptorType');
          }
          resolve(features);
        },
        (error) => {
          console.error(error);
          resolve(false);
        }
      );
    });
  }

  getFeatureToDisplay(pointClick: any, features: any) {
    features.forEach((feat: any) => {
      if (feat.geometry.type == 'Point') {
        feat['distance'] = turfDistance(
          turfHelper.point(pointClick),
          turfHelper.point(feat.geometry.coordinates)
        );
      } else {
        if (
          booleanPointInPolygon(
            turfHelper.point(pointClick),
            turfHelper.polygon(feat.geometry.coordinates)
          )
        ) {
          feat['distance'] = 0;
        } else {
          feat['distance'] = turfDistance(
            turfHelper.point(pointClick),
            turfCentroid(turfHelper.polygon(feat.geometry.coordinates))
          );
        }
      }
    });

    // TODO: Existem formas mais eficientes de retornar o menor valor.
    features.sort(
      (a: any, b: any) => parseFloat(a.distance) - parseFloat(b.distance)
    );

    return [features[0]];
  }

  closePopup() {
    if (this.popupOverlay) {
      const closer = document.getElementById('popup-closer');
      // @ts-ignore
      this.popupOverlay.setPosition(undefined);
      // @ts-ignore
      if (closer) closer.blur();
    }

    this.featureCollections = [];
    this.popupRegion = {
      coordinate: [],
      attributes: [],
      properties: {},
      geojson: {},
    };

    this.mapService.layers.forEach((layer) => {
      if (layer) {
        if (layer.get('key') === 'popup-vector') {
          this.mapService.removeLayer(layer);
        }
      }
    });
  }

  // TODO: Não esta mostrando info do ponto quando clicado, apenas do municipio.
  public onDisplayFeatureInfo(event: any): void {
    if (this.drawing) return;

    let map = this.mapService.map;

    let self = this;

    const currentLevel = this.drillDownLevel;

    // Resetando variveis de controle.
    if (!event.fromSearch) {
      this.closePopup();
    }

    this.wfsCard.nativeElement.style.visibility = 'hidden';

    // Transforma as coordenadas do click para a projeção desejada.
    this.popupRegion.coordinate = transform(
      event.coordinate,
      'EPSG:3857',
      'EPSG:4326'
    );

    const bufferedPoint = buffer(
      { type: 'Point', coordinates: this.popupRegion.coordinate },
      0.0001,
      {
        units: 'kilometers',
      }
    );

    const bufferSource = new VectorSource({
      features: new GeoJSON().readFeatures(bufferedPoint, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857',
      }),
    });

    const bbox = transformExtent(
      bufferSource.getExtent() as Extent,
      'EPSG:3857',
      'EPSG:4326'
    );

    const pixel: any = event.originalEvent?.clientX !== 0 && event.originalEvent ? map.getEventPixel(event.originalEvent) : null;
    let promises: any[] = [];

    if (currentLevel === 0) {
      promises.push(this.getFeatures('estados', bbox));
    } else if (currentLevel === 1) {
      promises.push(this.getFeatures('municipios_info', bbox));
    } else {
      // Always query malha fundiaria at level 2
      promises.push(this.getFeatures('malha_fundiaria_ambiental', bbox));

      if (pixel) {
        map.forEachFeatureAtPixel(pixel, function (layer: any) {
          const layerType: DescriptorType = layer.get('descriptorType');

          if (
            layer.get('type') === 'layertype' &&
            layerType.typeLayer === 'vectorial' &&
            layer.getVisible() &&
            layerType.wfsMapCard.show
          ) {
            promises.push(self.getFeatures(layer, bbox));
          }
        });
      }
    }

    let centroidCoordinate: number[] | null = null;

    Promise.all(promises).then((layersFeatures) => {
        console.log('--- MAP FEATURE INFO ---');
        console.log('Current DrillDown Level:', currentLevel);

        layersFeatures.forEach((featureCollection, index) => {
          if (featureCollection && featureCollection.features && featureCollection.features.length > 0) {
            const layerName = featureCollection.layerType ? featureCollection.layerType.viewValueType : (featureCollection.typeName || 'Unknown Layer');
            console.log(`Layer [${index}]: ${layerName} (${featureCollection.typeName})`);
            console.log('Features found:', featureCollection.features.length);
            featureCollection.features.forEach((f, i) => {
               console.log(`  Feature [${i}] Properties:`, f.properties);
            });
          }
        });

        console.log('Full Data:', layersFeatures);
        
        if (Array.isArray(layersFeatures) && layersFeatures.length <= 0) {
          console.error("No features found.")
          return;
        }

        let hasIncremented = false;

        layersFeatures.forEach((featureCollection, index) => {
          if (featureCollection.features.length <= 0) return;

          if (currentLevel < 2) {
            this.featureCollections.push(featureCollection);
            if (!hasIncremented) {
              const feature = featureCollection.features[0];
              const olFeature = new GeoJSON().readFeature(feature, {
                dataProjection: 'EPSG:4326',
                featureProjection: 'EPSG:3857',
              }) as any;
              const extent = olFeature.getGeometry()!.getExtent();

              if (!event.fromSearch) {
                map.getView().fit(extent, { duration: 1500 });
              }
              this.drillDownLevel++;
              this.refreshDrillDownLimits();

              // Apply region filter based on drill-down level
              if (currentLevel === 0 && feature.properties?.uf) {
                this.regionFilterService.updateRegionFilter({
                  type: 'state',
                  value: feature.properties.uf,
                  text: feature.properties.estado || '',
                });
              } else if (currentLevel === 1 && feature.properties?.cd_geocmu) {
                this.regionFilterService.updateRegionFilter({
                  type: 'city',
                  value: feature.properties.cd_geocmu,
                  text: feature.properties.municipio || '',
                });
              }

              hasIncremented = true;
            }
          } else {
            featureCollection.features = this.getFeatureToDisplay(
              this.popupRegion.coordinate,
              featureCollection.features
            );

            // Zoom to the parcel on Level 2
            if (index === 0 && featureCollection.features.length > 0) {
              const feature = featureCollection.features[0];
              const olFeature = new GeoJSON().readFeature(feature, {
                dataProjection: 'EPSG:4326',
                featureProjection: 'EPSG:3857',
              }) as any;
              const extent = olFeature.getGeometry()!.getExtent();
              if (!event.fromSearch) {
                map.getView().fit(extent, { duration: 1000 });
              }
            }

            if (index === 0) {
              this.popupRegion.geojson = featureCollection;
              this.popupRegion.properties =
                featureCollection.features[0].properties;

              // Calculate centroid of the feature for popup positioning
              const featureGeoJSON = featureCollection.features[0];
              const centroid = turfCentroid(featureGeoJSON);
              centroidCoordinate = transform(
                centroid.geometry.coordinates,
                'EPSG:4326',
                'EPSG:3857'
              );
            }

            if (currentLevel === 2 && index === 0) {
              featureCollection.layerType = {
                viewValueType: this.localizationService.translate(
                  'popup-info.malha_fundiaria'
                ),
                wfsMapCard: {
                  show: true,
                  attributes: [],
                },
              };
              this.featureCollections.push(featureCollection);
              this.mapAPIService.getLayerAttributes('malha_fundiaria_ambiental').subscribe({
                next: (response: any) => {
                  featureCollection.layerType.wfsMapCard.attributes = response;
                  this.popupRegion.attributes = response;
                }
              });

              // Publish the selected malha_fundiaria feature so the
              // statistics sidebar can fetch its vegetation time series,
              // and ask the parent to auto-open the sidebar.
              if (
                featureCollection.features &&
                featureCollection.features.length > 0
              ) {
                const selectedFeature = featureCollection.features[0];
                this.selectedFeatureService.set({
                  idLayer: 'malha_fundiaria_ambiental',
                  properties: selectedFeature.properties ?? null,
                  geometry: selectedFeature,
                });
                this.openStatisticsSidebar.emit();
              }
            } else if (featureCollection.hasOwnProperty('layerType')) {
              this.featureCollections.push(featureCollection);
            } else {
              this.mapAPIService.getMunicipalitiesAtributes().subscribe({
                next: (response) => {
                  this.popupRegion.attributes = response;
                },
              });
            }
          }
        });

        if (this.featureCollections.length > 0) {
          this.featureCollections.forEach((featureJson) => {
            const vectorSource = new VectorSource({
              features: new GeoJSON().readFeatures(featureJson, {
                dataProjection: 'EPSG:4326',
                featureProjection: 'EPSG:3857',
              }),
            });
            const vectorLayer = new VectorLayer({
              source: vectorSource,
              // @ts-ignore
              style: (feature) => {
                const type = feature.getGeometry()!.getType();
                const baseStyle = this.geoJsonStyles[type];
                if (currentLevel < 2 && (type === 'Polygon' || type === 'MultiPolygon')) {
                  return new Style({
                    stroke: new Stroke({
                      color: PRIMARY_COLOR,
                      width: 2,
                    }),
                    fill: new Fill({
                      color: 'rgba(0, 0, 0, 0)',
                    }),
                  });
                }
                return baseStyle;
              },
              properties: {
                key: 'popup-vector',
              },
              visible: true,
              zIndex: 100000,
            });
            this.mapService.addLayer(vectorLayer);
          });
        }

        if (
          this.popupRegion.geojson.hasOwnProperty('features') &&
          this.featureCollections.length <= 0
        ) {
          const vectorSource = new VectorSource({
            features: new GeoJSON().readFeatures(this.popupRegion.geojson, {
              dataProjection: 'EPSG:4326',
              featureProjection: 'EPSG:3857',
            }),
          });
          const vectorLayer = new VectorLayer({
            source: vectorSource,
            // @ts-ignore
            style: (feature) => {
              const type = feature.getGeometry()!.getType();
              const baseStyle = this.geoJsonStyles[type];
              if (currentLevel < 2 && (type === 'Polygon' || type === 'MultiPolygon')) {
                return new Style({
                  stroke: new Stroke({
                    color: PRIMARY_COLOR,
                    width: 2,
                  }),
                  fill: new Fill({
                    color: 'rgba(0, 0, 0, 0)',
                  }),
                });
              }
              return baseStyle;
            },
            properties: {
              key: 'popup-vector',
            },
            visible: true,
            zIndex: 100000000,
          });
          this.mapService.addLayer(vectorLayer);
        }

        if (this.featureCollections.length === 0) {
          this.closePopup();
          return;
        }

        if (currentLevel < 2) {
          return;
        }

        this.wfsCard.nativeElement.style.visibility = 'visible';
        this.wfsCard.nativeElement.style.bottom = '12px';
        this.wfsCard.nativeElement.style.left = '-50px';

        const container = document.getElementById('popup');

        if (this.popupOverlay) {
          map.removeOverlay(this.popupOverlay);
        }

        // @ts-ignore
        this.popupOverlay = new Overlay({
          id: 'popup-info',
          element: container!,
          autoPan: false,
        });
        this.popupOverlay.setPosition(centroidCoordinate || event.coordinate);
        map.addOverlay(this.popupOverlay);
      })
      .catch((error) => {
        console.error(error);
      });
  }

  public getAttributeValue(type: any, value: any) {
    if (value === null || value === undefined || value === '') return '';

    const lang = this.localizationService.currentLang();
    const locale = lang === 'pt' ? 'pt-BR' : 'en-US';

    let columnType = type;
    if (typeof type === 'object' && type !== null) {
      columnType = type.columnType;
    }

    // Attempt to convert to number if it's a numeric string
    const numValue =
      typeof value === 'string' && value.trim() !== ''
        ? Number(value.replace(',', '.'))
        : value;
    const isNumeric = typeof numValue === 'number' && !isNaN(numValue);

    // If it's numeric, we apply rounding rules regardless of the explicit columnType
    // (unless it's explicitly an integer)
    if (isNumeric && columnType !== 'integer') {
      return this.decimalPipe.transform(numValue, '1.0-2', locale) || value;
    }

    switch (columnType) {
      case 'integer':
        return this.decimalPipe.transform(numValue, '1.0-0', locale) || value;
      case 'date':
        return value;
      case 'string':
        return value;
      default:
        return value;
    }
  }

  public loadVideo(key: any) {
    if (key === 'videos_drone') {
      const player = this.video.nativeElement;
      if (player) {
        player.load();
      }
    }
  }

  private mapSearchCategoryToRegionFilterType(searchType: string): string | null {
    const typeMap: { [key: string]: string } = {
      'estado': 'state',
      'municipio': 'city',
      'bioma': 'biome',
    };
    return typeMap[searchType] || null;
  }

  public onSearchMalha(event: any): void {
    this.malhaSearchLoading = true;
    this.mapAPIService.getSearchCategory(this.searchCategory, event.query).subscribe((res) => {
      this.malhaSearchSuggestions = res.search;
      this.malhaSearchLoading = false;
    });
  }

  public onKeyUpMalha(event: KeyboardEvent): void {
    if (event.key === 'Enter' && this.malhaSearchSuggestions.length > 0) {
      this.onSelectMalha(this.malhaSearchSuggestions[0]);
    }
  }

  public onSelectMalha(event: any): void {
    const item = event.value || event;
    
    // 1. Clear previous state BEFORE adding the new layer
    this.closePopup();

    if (this.malhaVectorLayer) {
      this.mapService.removeLayer(this.malhaVectorLayer);
    }

    this.malhaSearchValue = item;
    
    if (!item || !item.geojson) return;

    const geojson = typeof item.geojson === 'string' ? JSON.parse(item.geojson) : item.geojson;

    let vectorSource = new VectorSource({
      features: new GeoJSON().readFeatures(geojson, {
        dataProjection: 'EPSG:4326',
        featureProjection: 'EPSG:3857',
      }),
    });

    this.malhaVectorLayer = new VectorLayer({
      zIndex: 100001,
      source: vectorSource,
      properties: {
        key: 'popup-vector',
        type: 'search',
      },
      style: [
        new Style({
          stroke: new Stroke({ color: PRIMARY_COLOR, width: 4 }),
          fill: new Fill({ color: 'rgba(0, 0, 0, 0)' }),
        }),
      ],
    });

    this.mapService.addLayer(this.malhaVectorLayer);
    let extent = this.malhaVectorLayer.getSource().getExtent();
    this.mapService.map.getView().fit(extent, { duration: 1000 });

    if (this.searchCategory === 'malha') {
      // Force drill down level to 2 for property search results
      this.drillDownLevel = 2;
      this.refreshDrillDownLimits();

      // Use centroid to fetch full information by simulating a click
      const centroid = turfCentroid(geojson);
      const coord3857 = transform(centroid.geometry.coordinates, 'EPSG:4326', 'EPSG:3857');

      this.onDisplayFeatureInfo({
        coordinate: coord3857,
        fromSearch: true,
        originalEvent: {
          clientX: 0,
          clientY: 0
        }
      });
    }

    // Update statistics sidebar when a state, municipality, or biome is selected
    const regionFilterType = this.mapSearchCategoryToRegionFilterType(item.type);
    if (regionFilterType) {
      this.regionFilterService.updateRegionFilter({
        type: regionFilterType,
        value: item.value,
        text: item.text,
      });
    }
  }

  public onClearMalhaSearch(): void {
    this.malhaSearchValue = { text: '' };
    if (this.malhaVectorLayer) {
      this.mapService.removeLayer(this.malhaVectorLayer);
    }
    this.closePopup();

    // Reset drill-down level and zoom to default Brazil view
    this.drillDownLevel = 0;
    this.mapService.resetZoom();
    this.refreshDrillDownLimits();

    // Reset region filter to national data
    this.regionFilterService.updateRegionFilter(DEFAULT_REGION);
  }
}
