import React from 'react';
import Headeur from './layout/Headeur';
import Project from './components/Project';
import pharmacie from '../public/images/pharmacie.jpg'
import binary from '../public/images/binary.jpg'

const Experience = () => {
    return (
    <div className='home experience'>
        <Headeur/>
        <section>
            <h1>Mon experience</h1>
            <p> J ai réalisé le site vitrine du cabinet d avocat parisien ASTEN AVOCATS  </p>
            <p> DECRIPTION </p>
            <Project img={pharmacie} text={"dans ce projet bakjdakjzfjapefjepofej"}></Project>
            <Project img={binary} text={"dans ce projet bakjdakjzfjapefjepofej"}></Project>
        </section>
    </div>
    );
};

export default Experience;