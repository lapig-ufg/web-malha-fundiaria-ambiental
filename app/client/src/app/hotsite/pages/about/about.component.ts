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
      role: 'Coordinator of the Pasture Research Program',
    },
    {
      name: 'Bernard Silva de Oliveira',
      image: 'assets/hotsite/images/team/bernard.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      role: 'PhD Candidate & Research Assistant',
    },
    {
      name: 'Ana Paula Matos e Silva',
      image: 'assets/hotsite/images/team/ana_silva.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      role: 'Doctoral Candidate & Research Assistant',
    },
    {
      name: 'Tharles de Sousa Andrade',
      image: 'assets/hotsite/images/team/tharles.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      role: 'Development Analyst',
    },
    {
      name: 'Felipe Jesus',
      image: 'assets/hotsite/images/team/felipe.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      role: 'Research Fellow in Geoprocessing and Remote Sensing',
    },
    {
      name: 'Guilherme Ramos Vaz',
      image: 'assets/hotsite/images/team/guilherme.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      role: 'Scientific Research Fellow in Environmental Analysis',
    },
    {
      name: 'Ana Paula Carlos Assunção',
      image: 'assets/hotsite/images/team/ana_assuncao.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      role: 'Research fellow in Geoprocessing and Visual Interpretation',
    },
    {
      name: 'Tiago Goncalves Maia Geraldine',
      image: 'assets/hotsite/images/team/tiago.jpeg',
      lattes: 'http://lattes.cnpq.br/',
      role: 'Development Analyst',
    },
    
  ];
}
