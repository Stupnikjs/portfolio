import React from 'react';
import Image from 'next/image';

const Project = (props) => {
    console.log(props)
    return (
        <div className='project'>
            <Image src={props.img} alt="" />
            <p>{props.text}</p>
        </div>
    );
};

export default Project;