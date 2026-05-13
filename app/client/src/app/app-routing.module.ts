import { NgModule } from '@angular/core';
import { ExtraOptions, RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  {
    path: '',
    loadChildren: () => import('./map-platform/components.module')
      .then(module => module.ComponentsModule),
  },
  {
    path: 'results',
    loadChildren: () => import('./analysis/analysis.module')
      .then(module => module.AnalysisModule),
  }
];

const config: ExtraOptions = {
  useHash: false,
}

@NgModule({
  imports: [RouterModule.forRoot(routes, config)],
  exports: [RouterModule]
})

export class AppRoutingModule { }
