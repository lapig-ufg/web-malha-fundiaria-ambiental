import { Component, OnInit } from '@angular/core';
import { LocalizationService } from "../../../@core/internationalization/localization.service";
import { LangChangeEvent } from "@ngx-translate/core";

import { Article } from '@core/interfaces';

@Component({
  standalone: false,
  selector: 'app-articles',
  templateUrl: './articles.component.html',
  styleUrls: ['./articles.component.scss']
})
export class ArticlesComponent implements OnInit {

  public search: string = '';
  public articles: Article[] = [];
  public lang: string;

  private allArticles = [
    {
      "doi": "https://doi.org/10.1126/science.abq7768",
      "authors": "De Marco Jr., P. et al.",
      "published": "2023-04-21",
      "image": "assets/hotsite/images/articles/the_value_of_private_properties_for_the_conservation_of_biodiversity_in_the_brazilian_cerrado.png",
      "pt": {
        "title": "O valor das propriedades privadas para a conservação da biodiversidade no Cerrado brasileiro",
        "abstract": "Áreas reservadas para conservação em terras privadas podem ser fundamentais para melhorar paisagens favoráveis à biodiversidade. Essa estratégia de conservação deve ser especialmente eficaz em regiões altamente ameaçadas que são mal protegidas por terras públicas, como o Cerrado brasileiro. Determinamos que áreas protegidas privadas acomodam até 14,5% das distribuições de espécies de vertebrados ameaçadas, o que aumenta para 25% ao considerar a distribuição do habitat nativo restante."
      },
      "en": {
        "title": "The value of private properties for the conservation of biodiversity in the Brazilian Cerrado",
        "abstract": "Areas set aside for conservation within private lands may be key to enhancing biodiversity-friendly landscapes. This conservation strategy should be especially effective in highly threatened regions that are poorly protected by public lands, such as the Brazilian Cerrado. We determined that private protected areas accommodate up to 14.5% of threatened vertebrate species ranges, which increases to 25% when considering the distribution of remaining native habitat."
      }
    },
    {
      "doi": "https://doi.org/10.1088/1748-9326/acd20a",
      "authors": "Camara, G. et al.",
      "published": "2023-05-12",
      "image": "assets/hotsite/images/articles/impact_of_land_tenure_on_deforestation_control_and_forest_restoration_in_brazilian_amazonia.png",
      "pt": {
        "title": "Impacto da posse da terra no controle do desmatamento e na restauração florestal na Amazônia brasileira",
        "abstract": "Este estudo examina como a estrutura fundiária restringe a capacidade do Brasil de cumprir suas metas de controle do desmatamento e restauração florestal no bioma Amazônia. Os resultados mostram que grande parte do desmatamento ocorre em propriedades privadas e apontam para a necessidade de combinar estratégias de comando e controle com políticas de mercado para alcançar os objetivos ambientais do país."
      },
      "en": {
        "title": "Impact of land tenure on deforestation control and forest restoration in Brazilian Amazonia",
        "abstract": "This study examines how land tenure constrains Brazil's ability to meet its deforestation control and forest restoration goals in its Amazonia biome. Findings show that a large portion of deforestation occurs on private lands, highlighting the need to combine robust command-and-control strategies with market-based policies to achieve the country's environmental targets."
      }
    },
    {
      "doi": "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/lei/l12651.htm",
      "authors": "Presidência da República, Brasil",
      "published": "2012-05-25",
      "image": "assets/hotsite/images/articles/lei_12651_codigo_florestal.png",
      "pt": {
        "title": "Lei nº 12.651, de 25 de maio de 2012 (Código Florestal Brasileiro)",
        "abstract": "Estabelece normas gerais sobre a proteção da vegetação nativa, Áreas de Preservação Permanente (APP) e áreas de Reserva Legal. A lei dispõe sobre a exploração florestal, controle de incêndios e instrumentos econômicos para conciliar o uso produtivo da terra com a preservação ambiental."
      },
      "en": {
        "title": "Law No. 12,651, of May 25, 2012 (Brazilian Forest Code)",
        "abstract": "Establishes general rules for the protection of native vegetation, Permanent Preservation Areas (APP), and Legal Reserves. The law regulates forest exploitation, fire control, and economic instruments to reconcile productive land use with environmental preservation."
      }
    },
    {
      "doi": "",
      "authors": "Cerignoni, F.",
      "published": "2023-09-01",
      "image": "assets/hotsite/images/articles/malha_car_livre_de_sobreposicao.png",
      "pt": {
        "title": "Nota Técnica: Malha CAR Livre de Sobreposição",
        "abstract": "A criação do Cadastro Ambiental Rural (CAR) foi um avanço para o diagnóstico ambiental e planejamento de propriedades rurais no Brasil. No entanto, devido ao caráter autodeclaratório e à metodologia de registro, existem muitas sobreposições entre imóveis que dificultam análises em escalas regionais. Essa nota descreve a metodologia para a limpeza das sobreposições do CAR em todo o território nacional."
      },
      "en": {
        "title": "Technical Note: CAR Mesh Free of Overlaps",
        "abstract": "The creation of the Rural Environmental Registry (CAR) was an advance for environmental diagnosis and rural property planning in Brazil. However, due to its self-declaratory nature and registration methodology, there are many overlaps between properties that hinder regional-scale analyses. This note describes the methodology for cleaning CAR overlaps throughout the national territory."
      }
    }
  ];

  constructor(private localizationService: LocalizationService) {
    this.lang = this.localizationService.currentLang();
    this.updateArticles();
  }

  ngOnInit() {
    this.localizationService.translateService.onLangChange.subscribe((langChangeEvent: LangChangeEvent) => {
      this.lang = langChangeEvent.lang;
      this.updateArticles();
    });
  }

  private updateArticles(): void {
    const language = this.lang === 'pt' ? 'pt' : 'en';
    
    this.articles = this.allArticles.map(article => ({
      title: article[language].title,
      abstract: article[language].abstract,
      doi: article.doi,
      authors: article.authors,
      published: article.published,
      image: article.image
    }));

    this.articles = this.articles.sort((a, b) => (a.published > b.published) ? -1 : 1);
  }
}