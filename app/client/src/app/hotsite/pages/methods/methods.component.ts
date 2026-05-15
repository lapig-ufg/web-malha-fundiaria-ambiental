import { Component, OnInit, HostListener, ElementRef } from '@angular/core';
import { LocalizationService } from "../../../@core/internationalization/localization.service";
import { LangChangeEvent } from "@ngx-translate/core";
import { environment } from 'src/environments/environment';
import { ContentHub } from '../../services/content-hub.service';

import { Method } from '@core/interfaces';

@Component({
  standalone: false,
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
    private contentHub: ContentHub,
    private el: ElementRef) {
    this.initStaticData();
    this.fetchMethodologies();

    this.lang = this.localizationService.currentLang();
  }

  @HostListener('window:scroll', ['$event'])
  onScroll() {
    const wrapper = this.el.nativeElement.querySelector('.methodology-diagram-wrapper');
    const img = this.el.nativeElement.querySelector('.diagram-image');
    const progressBar = this.el.nativeElement.querySelector('.progress-bar-fill');
    if (!wrapper || !img || !progressBar) return;

    const rect = wrapper.getBoundingClientRect();
    const scrollPos = -rect.top;
    const containerHeight = wrapper.clientHeight - window.innerHeight;
    
    if (scrollPos >= 0 && scrollPos <= containerHeight) {
      const progress = scrollPos / containerHeight;
      
      // Horizontal reveal: move the image left as the user scrolls down
      const imgWidth = img.clientWidth;
      const viewportWidth = window.innerWidth;
      const maxTranslateX = Math.max(0, imgWidth - viewportWidth);
      
      img.style.transform = `translateX(-${progress * maxTranslateX}px)`;
      
      // Update progress bar
      progressBar.style.width = `${progress * 100}%`;
    } else if (scrollPos < 0) {
      img.style.transform = 'translateX(0)';
      progressBar.style.width = '0%';
    } else if (scrollPos > containerHeight) {
      const imgWidth = img.clientWidth;
      const viewportWidth = window.innerWidth;
      const maxTranslateX = Math.max(0, imgWidth - viewportWidth);
      img.style.transform = `translateX(-${maxTranslateX}px)`;
      progressBar.style.width = '100%';
    }
  }

  private initStaticData() {
    this.staticMethodologies = [
      {
        number: '01.',
        title_pt: 'Ingestão dos Dados',
        title_en: 'Ingestão dos Dados',
        desc_pt: 'Coleta e organização de bases fundiárias e territoriais, incluindo propriedades privadas, terras indígenas e unidades de conservação',
        desc_en: 'Coleta e organização de bases fundiárias e territoriais, incluindo propriedades privadas, terras indígenas e unidades de conservação'
      },
      {
        number: '02.',
        title_pt: 'Pré-processamento',
        title_en: 'Pré-processamento',
        desc_pt: 'Correção de inconsistências geométricas, padronização das bases e remoção de duplicidades e registros inválidos',
        desc_en: 'Correção de inconsistências geométricas, padronização das bases e remoção de duplicidades e registros inválidos'
      },
      {
        number: '03.',
        title_pt: 'Hierarquização',
        title_en: 'Hierarquização',
        desc_pt: 'Definição de prioridades entre as camadas territoriais por meio de análise multicritério, garantindo coerência em casos de sobreposição',
        desc_en: 'Definição de prioridades entre as camadas territoriais por meio de análise multicritério, garantindo coerência em casos de sobreposição'
      },
      {
        number: '04.',
        title_pt: 'Reclassificação das camadas',
        title_en: 'Reclassificação das camadas',
        desc_pt: 'As camadas fundiárias são convertidas para formato raster, organizadas em uma grade contínua onde cada pixel representa a prioridade definida pelo método AHP',
        desc_en: 'As camadas fundiárias são convertidas para formato raster, organizadas em uma grade contínua onde cada pixel representa a prioridade definida pelo método AHP'
      },
      {
        number: '05.',
        title_pt: 'Análise de sobreposição',
        title_en: 'Análise de sobreposição',
        desc_pt: 'Os conflitos entre camadas são resolvidos mantendo, em cada pixel, a classe fundiária de maior prioridade. Em seguida, os vetores originais são recuperados para compor a malha final',
        desc_en: 'Os conflitos entre camadas são resolvidos mantendo, em cada pixel, a classe fundiária de maior prioridade. Em seguida, os vetores originais são recuperados para compor a malha final'
      },
      {
        number: '06.',
        title_pt: 'Integração Ambiental',
        title_en: 'Integração Ambiental',
        desc_pt: 'Os ativos ambientais são incorporados à malha fundiária, permitindo análises de conformidade e a geração de estatísticas ambientais associadas ao território',
        desc_en: 'Os ativos ambientais são incorporados à malha fundiária, permitindo análises de conformidade e a geração de estatísticas ambientais associadas ao território'
      }
    ];
  }

  ngOnInit() {
    this.localizationService.translateService.onLangChange.subscribe((langChangeEvent: LangChangeEvent) => {
      this.fetchMethodologies();
      this.lang = langChangeEvent.lang;
    });
  }

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
