import React from 'react';
import PP from './PP';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faNodeJs, faJs, faCss3, faHtml5, faReact } from '@fortawesome/free-brands-svg-icons';
import { faBriefcase, faBuildingColumns, faGlobe, faPerson } from '@fortawesome/free-solid-svg-icons';
import Image from 'next/image';
import drapeauFr from "../../public/images/France.png"
import drapeauEn from "../../public/images/anglais.png"
import drapeauEs from "../../public/images/espagne.png"
import Link from 'next/link';


const Cv = () => {
    return (
        <div className='cv shadow-slate-500 bg-slate-300'>
           <aside>
            <PP></PP>
            <div className='contact'>
                <h2>Nicolas Boudier</h2>
                <p> Née le 21/11/1990 au Mans </p>
                <p> 26ter route des gachets, 33370 SALLEBOEUF</p>
            </div>
            <div className='lienspro'>
                <Link href="https://github.com/Stupnikjs">github.com/Stupnikjs</Link>
                <Link href="https://www.linkedin.com/in/nicolas-boudier-1a0392239/">linkedin.com/in/nicolas-boudier-1a0392239/</Link>
                <Link href="#">n.boudier.ph@gmail.com</Link>
            </div>
            <div className='langues'>
                <p> <Image src={drapeauFr}/> Francais, langue maternelle </p>
                <p> <Image src={drapeauEn}/> Anglais, professionel </p>
                <p> <Image src={drapeauEs}/> Espagnol, basique </p>
            </div>

           </aside>
           
           <section className='mainSection'>
           <h1> Developpeur Web Javascript/REACT <FontAwesomeIcon icon={faReact}/> </h1>
            <article>
                <h2> <FontAwesomeIcon icon={faBriefcase}></FontAwesomeIcon> Experience Professionelle  </h2>
                <ul>
                    <li> Pharmacien diplomé depuis 2018,  en exercice dans une pharmacie de centre ville </li>
                    <li> Realisation du site vitrine du Cabinet Parisien Asten-Avocats</li>
                
                    
                </ul>
            </article>
            <article>
                <h2><FontAwesomeIcon icon={faBuildingColumns}></FontAwesomeIcon>  Formations   </h2>
                <ul>
                    <li> Doctorat en Pharmacie de la Faculté de Pharmacie de Tours </li>
                    <li> Developpement Web en autodidacte </li>
                </ul>
            </article>
            <article>
                <h2>  <FontAwesomeIcon icon={faGlobe}></FontAwesomeIcon>Competences developpement Web</h2>
                <ul id='devskills'>
                    <li> HTML <FontAwesomeIcon icon={faHtml5}></FontAwesomeIcon> </li>
                    <li> CSS <FontAwesomeIcon icon={faCss3}></FontAwesomeIcon> </li>
                    <li> JAVASCRIPT <FontAwesomeIcon icon={faJs}></FontAwesomeIcon> </li>
                    <li> NODE JS <FontAwesomeIcon icon={faNodeJs}></FontAwesomeIcon></li>
                    
                </ul>
            </article>
            <article>
                <h2><FontAwesomeIcon icon={faPerson}></FontAwesomeIcon>  Soft Skills </h2>
                <ul>
                    <li> Relation client, ecoute, empathie </li>
                    <li> Connaisances médicales avancées  </li>

                </ul>
            </article>

           </section>
        </div>
    );
};

export default Cv;