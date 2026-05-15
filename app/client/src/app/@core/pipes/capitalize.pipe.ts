import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  standalone: false, name: 'capitalize' })
export class CapitalizePipe implements PipeTransform {

  transform(input: string): string {
    return input && input.length
      ? (input.charAt(0).toUpperCase() + input.slice(1).toLowerCase())
      : input;
  }
}
