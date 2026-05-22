/**
 * Angular imports.
 */
import { Component, ChangeDetectorRef } from '@angular/core';

import { LocalizationService } from '../../../@core/internationalization/localization.service';
import { Menu } from '@core/interfaces';
import { environment } from 'src/environments/environment';

@Component({
  standalone: false,
  selector: 'app-main',
  templateUrl: './main.component.html',
  styleUrls: ['./main.component.scss'],
})
export class MainComponent {
  public COMMIT_ID = `Build: ${environment.COMMIT_ID}`;

  public lang: string = 'pt';

  public menus: Array<Menu> = [
    {
      key: 'layers',
      icon: 'fg-layers',
      show: false,
    },
    {
      key: 'statistics',
      icon: 'bx bx-bar-chart-alt',
      show: false,
    },
    {
      key: 'options',
      icon: 'fg-map-options-alt',
      show: false,
    },
  ];

  get leftSidebarVisible(): boolean {
    return this.menus[0].show || this.menus[2].show;
  }

  set leftSidebarVisible(value: boolean) {
    if (!value) {
      this.menus[0].show = false;
      this.menus[2].show = false;
    }
  }

  constructor(
    private localizationService: LocalizationService,
    private cdRef: ChangeDetectorRef
  ) {}

  public onMenuClick(menu: Menu): void {
    menu.show = !menu.show;

    if (menu.key === 'statistics') return;

    this.menus.forEach((element: Menu) => {
      if (element.key === 'statistics') return;
      if (element.key === menu.key) return;
      element.show = false;
    });
  }

  /**
   * Executado quando a barra lateral esquerda é fechado. Reponsável por
   * fechar todos os menus alocados na barra lateral esquerda.
   */
  public onLeftSidebarClose(): void {
    this.menus[0].show = false;
    this.menus[2].show = false;
  }

  public isLeftSidebarToggle(): boolean {
    return !this.menus.every((element: Menu) => {
      if (element.key === 'statistics') return true;
      return !element.show;
    });
  }

  /**
   * Executado na iteração com os controladores de idioma. 
   * 
   * @param lang - String representando o idioma.
   */
  public changeLanguage(lang: string): void {
    this.lang = lang;

    this.localizationService.useLanguage(lang);
  }
}
