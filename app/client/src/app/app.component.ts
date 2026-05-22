import { Component, OnInit } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { PrimeNGConfig } from 'primeng/api';
import { TranslateService, LangChangeEvent } from '@ngx-translate/core';
import { environment } from "../environments/environment";

@Component({
  standalone: false,
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: []
})
export class AppComponent implements OnInit {
  constructor(
    private primengConfig: PrimeNGConfig,
    private translateService: TranslateService,
    private titleService: Title
  ) {
    const head = document.getElementsByTagName('head')[0];
    let googleTagURL = document.createElement('script');
    let gtag = document.createElement('script');

    googleTagURL.async = true;
    googleTagURL.src = `https://www.googletagmanager.com/gtag/js?id=${environment.GTAG}`
    gtag.innerHTML = `
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', '${environment.GTAG}');
    `;
    head.insertBefore(googleTagURL, head.lastChild);
    head.insertBefore(gtag, head.lastChild);
  }

  ngOnInit() {
    this.primengConfig.ripple = true;
    
    // Set initial title
    this.updateTitle();

    // Update title on language change
    this.translateService.onLangChange.subscribe((event: LangChangeEvent) => {
      this.updateTitle();
    });
  }

  private updateTitle() {
    this.translateService.get('hotsite.home.abstract.title').subscribe((res: string) => {
      this.titleService.setTitle(res);
    });
  }
}
