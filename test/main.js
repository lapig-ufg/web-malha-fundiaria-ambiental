import 'ol/ol.css';
import Map from 'ol/Map.js';
import {getView, withExtentCenter, withHigherResolutions} from 'ol/View.js';
import TileLayer from 'ol/layer/WebGLTile.js';
import GeoTIFF from 'ol/source/GeoTIFF.js';

const source = new GeoTIFF({
  normalize: false,
  interpolate: false,
  sources: [
    {
      url: 'https://s3.lapig.iesa.ufg.br/malha-fundiaria/brasil_malhafundiaria_ambiental_10m_v2_cog.tif',
    },
  ],
});

const map = new Map({
  target: 'map',
  layers: [
    new TileLayer({
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
      }
    }),
  ],
  view: getView(source, withHigherResolutions(1), withExtentCenter()),
});
