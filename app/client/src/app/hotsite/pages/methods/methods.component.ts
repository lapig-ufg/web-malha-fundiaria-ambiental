import { Component, OnInit } from '@angular/core';
import { LocalizationService } from "../../../@core/internationalization/localization.service";
import { LangChangeEvent } from "@ngx-translate/core";
import { environment } from 'src/environments/environment';
import { ContentHub } from '../../services/content-hub.service';

import { Method } from '@core/interfaces';

@Component({
  selector: 'app-methods',
  templateUrl: './methods.component.html',
  styleUrls: ['./methods.component.scss']
})
export class MethodsComponent implements OnInit {
  public methodologies: Method[] = [];
  public staticMethodologies: any[] = [];

  public lang: string;

  constructor(
    private localizationService: LocalizationService,
    private contentHub: ContentHub) {
    this.initStaticData();
    this.fetchMethodologies();

    this.lang = this.localizationService.currentLang();
  }

  private initStaticData() {
    this.staticMethodologies = [
      {
        icon: 'bx-data',
        title_pt: 'Fontes de Dados',
        title_en: 'Data Sources',
        desc_pt: 'Integração de bases oficiais como SIGEF/INCRA, CAR (SFB), SNUC e Terras Indígenas (FUNAI) para compor o mosaico territorial.',
        desc_en: 'Integration of official databases such as SIGEF/INCRA, CAR (SFB), SNUC, and Indigenous Lands (FUNAI) to compose the territorial mosaic.'
      },
      {
        icon: 'bx-layer',
        title_pt: 'Hierarquização Territorial',
        title_en: 'Territorial Hierarchy',
        desc_pt: 'Aplicação de regras de prevalência para resolver sobreposições espaciais entre diferentes categorias fundiárias e ambientais.',
        desc_en: 'Application of prevalence rules to resolve spatial overlaps between different land tenure and environmental categories.'
      },
      {
        icon: 'bx-shape-polygon',
        title_pt: 'Limpeza Topológica',
        title_en: 'Topological Cleaning',
        desc_pt: 'Processamento rigoroso para eliminação de vazios, duplicidades e inconsistências geométricas na malha consolidada.',
        desc_en: 'Rigorous processing to eliminate gaps, duplications, and geometric inconsistencies in the consolidated mesh.'
      },
      {
        icon: 'bx-code-alt',
        title_pt: 'Processamento Automatizado',
        title_en: 'Automated Processing',
        desc_pt: 'Utilização de scripts Python (GeoPandas) e ferramentas de GIS para garantir a reprodutibilidade e precisão dos dados.',
        desc_en: 'Use of Python scripts (GeoPandas) and GIS tools to ensure data reproducibility and precision.'
      },
      {
        icon: 'bx-check-shield',
        title_pt: 'Consolidação e Validação',
        title_en: 'Consolidation & Validation',
        desc_pt: 'Geração do plano de informação final com classificação jurídica e administrativa validada conforme normas vigentes.',
        desc_en: 'Generation of the final information plan with legal and administrative classification validated according to current regulations.'
      },
      {
        icon: 'bx-globe',
        title_pt: 'Padronização Geoespacial',
        title_en: 'Geospatial Standardization',
        desc_pt: 'Conversão sistemática de todos os dados para o sistema de referência SIRGAS 2000, garantindo compatibilidade nacional.',
        desc_en: 'Systematic conversion of all data to the SIRGAS 2000 reference system, ensuring national compatibility.'
      }
    ];
  }

  ngOnInit() {
    this.localizationService.translateService.onLangChange.subscribe((langChangeEvent: LangChangeEvent) => {
      this.fetchMethodologies();
      this.lang = langChangeEvent.lang;
    });
  }

  /**
   * Recupera os elementos do *Methodologies*.
   */
  private fetchMethodologies(): void {
    this.contentHub.getMethodologies().subscribe(values => {
      this.methodologies = [];

      values.forEach((element: any) => {
        let fileUrl = JSON.parse(element.file as string)[0].download_link;

        this.methodologies.push(
          {
            title: element.title,
            image: environment.S3 + element.image,
            description: element.description,
            file: environment.S3 + fileUrl,
          });
      });
    })
  }
}
