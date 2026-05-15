import { PipeTransform, Pipe} from '@angular/core';
import { DomSanitizer } from "@angular/platform-browser";

@Pipe({
  standalone: false, name: 'safe' })
export class SafePipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) { }
  transform(url: any) {
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }
}
