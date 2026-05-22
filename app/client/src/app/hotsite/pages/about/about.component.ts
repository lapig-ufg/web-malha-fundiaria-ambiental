import { Component } from '@angular/core';

@Component({
  standalone: false,
  selector: 'app-about',
  templateUrl: './about.component.html',
  styleUrls: ['./about.component.scss'],
})
export class AboutCompenent {

  team = [
    {
      name: 'Laerte Guimarães Ferreira',
      image: 'assets/hotsite/images/team/laerte.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      roleKey: 'hotsite.about.team.roles.laerte',
    },
    {
      name: 'Bernard Silva de Oliveira',
      image: 'assets/hotsite/images/team/bernard.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      roleKey: 'hotsite.about.team.roles.bernard',
    },
    {
      name: 'Ana Paula Matos e Silva',
      image: 'assets/hotsite/images/team/ana_silva.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      roleKey: 'hotsite.about.team.roles.ana_silva',
    },
    {
      name: 'Tharles de Sousa Andrade',
      image: 'assets/hotsite/images/team/tharles.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      roleKey: 'hotsite.about.team.roles.tharles',
    },
    {
      name: 'Felipe Jesus',
      image: 'assets/hotsite/images/team/felipe.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      roleKey: 'hotsite.about.team.roles.felipe',
    },
    {
      name: 'Guilherme Ramos Vaz',
      image: 'assets/hotsite/images/team/guilherme.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      roleKey: 'hotsite.about.team.roles.guilherme',
    },
    {
      name: 'Ana Paula Carlos Assunção',
      image: 'assets/hotsite/images/team/ana_assuncao.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      roleKey: 'hotsite.about.team.roles.ana_assuncao',
    },
    {
      name: 'Tiago Goncalves Maia Geraldine',
      image: 'assets/hotsite/images/team/tiago.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      roleKey: 'hotsite.about.team.roles.tiago',
    },
  ];
}
