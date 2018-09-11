import React from 'react';
import PropTypes from 'prop-types';
import { FormattedMessage } from 'react-intl';
import { connect } from 'react-redux';
import { compose } from 'redux';
import { createStructuredSelector } from 'reselect';
import injectReducer from 'utils/injectReducer';
import injectSaga from 'utils/injectSaga';

import {
  makeSelectTargetLoading,
  makeSelectTargetError,
  makeSelectTarget
} from 'containers/App/selectors';

import { loadTarget } from '../App/actions';
import reducer from '../App/reducer';
import saga from './saga';

import { Grid, Alert } from 'react-bootstrap/lib';
import LoadingIndicator from 'components/LoadingIndicator';
import messages from './messages';

/* eslint-disable react/prefer-stateless-function */
export class Target extends React.PureComponent {
  componentDidMount() {
    this.props.onLoadTarget(this.props.targetId);
  }

  renderTarget(target) {
    if (target) {
      return (
        <Grid>
          {target.id} - {target.name}
        </Grid>
      );
    } else {
      return <div />
    }
  }

  render() {
    const { loading, error, target } = this.props;
    let alert = <div />;

    if (loading) {
      return <LoadingIndicator />;
    }

    if (error != false) {
      alert = <Alert bsStyle="danger" className="full-swidth"><strong>Error!</strong> {error.toString()}</Alert>
    }
    
    return (
      <Grid>
        <strong><FormattedMessage {...messages.header} /></strong>
        <br /><br />
        {this.renderTarget(target)}
        {alert}
      </Grid>
    );
  }
}

Target.propTypes = {
  loading: PropTypes.bool,
  error: PropTypes.any,
  target: PropTypes.any,
  targetId: PropTypes.any,
  onLoadTarget: PropTypes.func,
};

export function mapDispatchToProps(dispatch) {
  return {
    onLoadTarget: id => dispatch(loadTarget(id)),
  };
}

const mapStateToProps = createStructuredSelector({
  loading: makeSelectTargetLoading(),
  error: makeSelectTargetError(),
  target: makeSelectTarget(),
});

const withConnect = connect(
  mapStateToProps,
  mapDispatchToProps,
);

const withReducer = injectReducer({ key: 'target', reducer });
const withSaga = injectSaga({ key: 'target', saga });

export default compose(
  withReducer,
  withSaga,
  withConnect,
)(Target);