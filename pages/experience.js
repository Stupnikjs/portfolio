import React, {useState, useEffect} from 'react';
import Headeur from './layout/Headeur';
import Image from 'next/image';
import Link from 'next/link';
import AnimProject from "../components/AnimProject"
import photoAsten from "../public/images/asten-avocats.png"; 
import photoAsten2 from "../public/images/main-asten.png"; 
import photoPharmacie from '../public/images/pharmacie.jpg'
import {Playfair_Display} from '@next/font/google'; 

const playfair = Playfair_Display({ weight:"400", subsets: ['latin']})


const Experience = () => {

    
    const [scrollY, setScrollY] = useState(0); 
    const [scrolled, setScrolled] = useState(false)
    const [scrollTop, setScrollTop] = useState(false)
    const [displayArrow, setDisplayArrow] = useState(false)

    const scrollHandler= (e) => {

        const {scrollY} = window;
        const windowHeight = window.innerHeight 
        setScrollY(scrollY)
        if (scrollY > windowHeight) setDisplayArrow(true)
        else setDisplayArrow(false)
    }



    useEffect(() => {
      
        if (scrollY > 0) setScrolled(true)
        if (scrollY === 0) setScrolled(false)

        window.addEventListener("scroll", scrollHandler, {passive: true})
        if (scrollTop){ 
            window.scrollTo({ top: 0, behavior:"smooth"})
            setScrollTop(false)
        }
        
        return () => {
            window.removeEventListener("scroll", scrollHandler, { passive: true });
         }

    }, [scrollTop, scrollY]); 

    return (
    <div className={playfair.className}>
        <Headeur scrolled={scrolled}/>
        <main className='main-experience'>
                <h1 className='intro-experience-title'>Jugez de mes competences au travers des projets que j'ai realisé </h1>
                <h2>Mes réalisations </h2>
            <section className='section-experience-asten'>
                <Link href='#'><h2>Cabinet d'Avocat ASTEN </h2></Link>
                <AnimProject photos={[photoAsten, photoAsten2]}></AnimProject>
                
                <p> Utilisation de NEXT.js le framework React</p>
                <p> A partir d un projet initial sur WordPress </p>
                <p>Utilisation de Fontawsome et de Sass</p>
           
            </section>
            <section className='pharmacie'>
                <h2> Mon diplome de Pharmacien </h2>
                <article>
                    <Image src={photoPharmacie} alt="pharmacie"></Image>
                    <p>Bien qu'insatisfait par le rôle du Pharmacien, mon diplome et mon experience professionelle m'ont permis de develloper des capacitées d'empathie,  de management, et de travail sur soi.</p> 
                </article>
            </section>
        </main>
        
    </div>
    );
};

export default Experience;