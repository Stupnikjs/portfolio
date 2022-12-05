import React from 'react';
import Headeur from './layout/Headeur';
import Image from 'next/image';
import Link from 'next/link';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faTwitter, faGithub, faLinkedin } from '@fortawesome/free-brands-svg-icons';
import photoAsten from "../public/images/asten-avocats.png"; 
import photoAsten2 from "../public/images/main-asten.png"; 
import photoPharmacie from '../public/images/pharmacie.jpg'
import Vertical from './layout/Vertical';
import LinkShape from './components/LinkShape';


const Experience = () => {
    return (
    <div className='experience'>
        <Headeur/>
        <section className='intro-experience'>
            <h1 className='intro-experience-title'> Plus que les diplomes, vous pourrez juger de mes competences au travers des projets que j ai realisé </h1>
            <h2>Mes réalisations </h2>
             
            <article className='asten'>
            <Link href='#'><h2>Cabinet d Avocat ASTEN </h2></Link>
            <div className='photo-div'>
                <Image src={photoAsten} alt="asten-intro"></Image>  
                <Image src={photoAsten2} alt="asten-main" ></Image>   
            </div>
            <p> Utilisation de NEXT.js le framework React</p>
            <p> A partir d un projet initial sur WordPress </p>
            <p>Utilisation de Fontawsome et de Sass</p>
            </article> 
        </section>
        <section className='pharmacie'>
            <h2> Mon diplome de Pharmacien </h2>
            <article>
                <Image src={photoPharmacie} alt="pharmacie"></Image>
                <p> Bien qu insatisfait par le rôle du Pharmacien, mon diplome et mon experience professionelle m on permis de develloper des capacités d empathie de colaboration, de travail sur soi </p> 
            </article>
        </section>
        <LinkShape></LinkShape> 
    </div>
    );
};

export default Experience;