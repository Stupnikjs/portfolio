import React from 'react';
import StyleBar from '../components/styleBar';
import Round from '../components/Round';

const Intro = () => {
    
    let elarray = new Array(6).fill(1)

    let index = 0

    const returnStyle = (x,y, op) => {
        return {
            transform: `translateX(${x+15}%) scaleX(0.1) translateY(${y}%)`, 
            opacity: op,
            backgroundColor: "lightblue", 
            border: "0.7px solid grey"
        }
        
    }
    console.log(elarray)
    return (
        <div className='intro'>
            <p>Bonjour, je m'appelle </p>
            <h1><strong>Nicolas,</strong> Boudier </h1>
            <p>Developpeur <strong className='strong'>Javascript</strong> </p>
            <p> Fort d'une experience atypique, j'aspire à developper mes competences en participant a des projets </p>
           
            {
                elarray.map((element, index) => {
                    return (<StyleBar style={returnStyle(10*index,index*10,index/10)}> {element}</StyleBar>)
                })
            }
           
           
        </div>
    );
};

export default Intro;