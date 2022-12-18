import React from 'react';
import Image from 'next/image';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'; 
import { faLinkedinIn, faGithub } from '@fortawesome/free-brands-svg-icons';
import style from "./anim_project.module.css"

const ProLink = ({photos}) => {
    return (
        <div className={"anim_project"}>
         
            <div className={"cube"}>{
                         photos.map((element: any, index: number) => {
                    return <div key={index} className={"anim_item " + `anim_item${(index+1).toString()}` }><Image className='image' src={element} alt={element} /></div>
                })}
            </div>
        </div>
    );
};

export default ProLink;