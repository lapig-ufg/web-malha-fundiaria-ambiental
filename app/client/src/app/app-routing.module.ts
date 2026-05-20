import { NgModule } from '@angular/core';
import { ExtraOptions, RouterModule, Routes } from '@angular/router';

const routes: Routes = [
  {
    path: '',
    loadChildren: () => import('./hotsite/hotsite.module')
      .then(module => module.HotsiteModule,)
  },
  {
    path: 'map',
    loadChildren: () => import('./map-platform/components.module')
      .then(module => module.ComponentsModule),
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
