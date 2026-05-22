import { Component, OnInit, HostListener, ElementRef } from '@angular/core';
import { LocalizationService } from "../../../@core/internationalization/localization.service";
import { LangChangeEvent } from "@ngx-translate/core";

@Component({
  standalone: false,
  selector: 'app-methods',
  templateUrl: './methods.component.html',
  styleUrls: ['./methods.component.scss']
})
export class MethodsComponent implements OnInit {
  public staticMethodologies: any[] = [];
  public lang: string;

  constructor(
    private localizationService: LocalizationService,
    private el: ElementRef) {
    this.initStaticData();

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
      // account for 40px padding on each side (80px total gap needed in calculation)
      const imgWidth = img.clientWidth;
      const viewportWidth = window.innerWidth;
      const maxTranslateX = Math.max(0, imgWidth + 80 - viewportWidth);
      
      img.style.transform = `translateX(-${progress * maxTranslateX}px)`;
      
      // Update progress bar
      progressBar.style.width = `${progress * 100}%`;
    } else if (scrollPos < 0) {
      img.style.transform = 'translateX(0)';
      progressBar.style.width = '0%';
    } else if (scrollPos > containerHeight) {
      const imgWidth = img.clientWidth;
      const viewportWidth = window.innerWidth;
      const maxTranslateX = Math.max(0, imgWidth + 80 - viewportWidth);
      img.style.transform = `translateX(-${maxTranslateX}px)`;
      progressBar.style.width = '100%';
    }
  }

  private initStaticData() {
    this.staticMethodologies = [
      {
        number: '01.',
        title_key: 'hotsite.methods.items.1.title',
        desc_key: 'hotsite.methods.items.1.description'
      },
      {
        number: '02.',
        title_key: 'hotsite.methods.items.2.title',
        desc_key: 'hotsite.methods.items.2.description'
      },
      {
        number: '03.',
        title_key: 'hotsite.methods.items.3.title',
        desc_key: 'hotsite.methods.items.3.description'
      },
      {
        number: '04.',
        title_key: 'hotsite.methods.items.4.title',
        desc_key: 'hotsite.methods.items.4.description'
      },
      {
        number: '05.',
        title_key: 'hotsite.methods.items.5.title',
        desc_key: 'hotsite.methods.items.5.description'
      },
      {
        number: '06.',
        title_key: 'hotsite.methods.items.6.title',
        desc_key: 'hotsite.methods.items.6.description'
      }
    ];
  }

  ngOnInit() {
    this.localizationService.translateService.onLangChange.subscribe((langChangeEvent: LangChangeEvent) => {
      this.lang = langChangeEvent.lang;
    });
  }
}
