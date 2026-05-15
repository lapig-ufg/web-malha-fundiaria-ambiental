import { Component, OnInit } from '@angular/core';
import { ContentHub } from '../../services/content-hub.service';
import { LocalizationService } from 'src/app/@core/internationalization/localization.service';

@Component({
  standalone: false,
  selector: 'app-about',
  templateUrl: './about.component.html',
  styleUrls: ['./about.component.scss'],
})
export class AboutCompenent implements OnInit {

  constructor(
    private localizationService: LocalizationService,
    private contentHub: ContentHub,
  ) {
  }

  ngOnInit() {
  }
}
